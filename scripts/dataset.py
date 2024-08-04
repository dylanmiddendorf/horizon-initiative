import logging
from typing import Container, Iterable, cast

from api import CodeforcesAPI, LeetCodeAPI
import mysql.connector
from mysql.connector.errors import DataError, IntegrityError
from mysql.connector.types import RowItemType


# TODO utilize logging framework instead of `print()`
# TODO binary search for larger contests
# TODO enable users to specify verbosity


class CodeforcesDatasetBuilder:
    AUTHOR_BLOCK_SIZE = 512
    SUBMISSION_BLOCK_SIZE = 2048

    def __init__(self) -> None:
        self.cnx = mysql.connector.connect(
            host="172.24.112.1", user="wsl_root", password="root"
        )
        self.cursor = self.cnx.cursor()  # Used for processing queries
        self.cursor.execute("USE horizon_initiative;")
        self.api = CodeforcesAPI()  # Connect to the Codeforces API

    def load_metadata(self, contests: list[int]) -> None:
        for contest_id in contests:
            try:
                print(f"Fetching contest info for: {contest_id}")
                contest = self._fetch_contest_info(contest_id)
                # contest = (id, name, start_time, duration)
                end_time = contest[2] + contest[3]

                print("Fetching participant information")
                participants = self._fetch_contest_standings(contest_id)
                print("Fetching submission information")
                self._fetch_contest_submissions(contest_id, end_time, participants)
            except Exception as e:
                print(e)
                print(f"Error fetching info from contest {contest_id}")

    def _fetch_contest_info(
        self, contest_id: int, force=False
    ) -> tuple[int, str, int, int]:
        # Don't update the entry if it already exists
        contest = self._query_contest(contest_id)
        if not force and contest:
            return contest

        retval = self.api.get_contest_standings(contest_id, count=1)
        assert retval["status"] == "OK", f"Invalid API response: {retval['status']}"
        contest = retval["result"]["contest"]

        contest_name = contest["name"]
        contest_start_time = contest["startTimeSeconds"]
        contest_duration = contest["durationSeconds"]
        query = "INSERT INTO codeforces_contest (id, name, start_time, duration) VALUES (%s, %s, %s, %s)"
        values = (contest_id, contest_name, contest_start_time, contest_duration)

        self.cursor.execute(query, values)  # INSERT INTO [...] VALUES [...]
        return values  # Return the contest information, to prevent query

    def _fetch_contest_standings(self, contest_id: int) -> set[str]:
        participants = set()

        offset = 1  # Used to store the last row fetched
        while True:
            # For each block of requested rankings, we will obtain relevent
            # author metadata. Afterwords, we will obtain all associated
            # submission metadata with one request. As a result, this is able
            # to reduce the number of API calls by a considerable amount
            handles = []

            retval = self.api.get_contest_standings(
                contest_id, offset, self.AUTHOR_BLOCK_SIZE
            )
            assert retval["status"] == "OK", f"Invalid API response: {retval['status']}"
            contest_standings = retval["result"]

            for row in contest_standings["rows"]:
                party_memebers = row["party"]["members"]
                assert len(party_memebers) == 1, "Submission MUST contain one author"
                handles.append(party_memebers[0]["handle"])
            self._fetch_user_info(handles)
            self.cnx.commit()  # Commit all data to the database
            participants.update(handles)
            if len(contest_standings["rows"]) < self.AUTHOR_BLOCK_SIZE:
                break  # All participant standings have been recorded

            offset += self.AUTHOR_BLOCK_SIZE
        return participants

    def _fetch_contest_submissions(
        self,
        contest_id: int,
        end_time: int = None,
        participants: Container[str] = None,
    ) -> None:
        if len(participants) == 0:
            print(f"No participants found for contest {contest_id}")
            return
        if end_time is None:
            self.cursor.execute(
                f"SELECT * FROM codeforces_contest WHERE id={contest_id}"
            )
            contest = self.cursor.fetchall()[0]  # Calculate the contest end time
            end_time = contest["start_time"] + contest["duration"]

        low_offset, high_offset = 0, 5_000_000  # Used to store the last row fetched

        # Binary Search to prevent linearly probing through up-to 1.4m submissions
        while (high_offset - low_offset) > 2000:
            offset = low_offset + (high_offset - low_offset) // 2
            print(offset)
            retval = self.api.get_contest_status(contest_id, offset=offset, count=1)
            assert retval["status"] == "OK", "Invalid API response"
            if len(retval["result"]) == 0:
                high_offset = offset - 1
                continue

            assert len(retval["result"][0]["author"]["members"]) == 1
            submission_time = retval["result"][0]["creationTimeSeconds"]
            if submission_time < end_time:
                high_offset = offset - 1
            else:
                low_offset = offset + 1
        offset = max(1, offset - 2001)
        print(f"final offset: {offset}")
        while True:
            retval = self.api.get_contest_status(
                contest_id, offset=offset, count=self.SUBMISSION_BLOCK_SIZE
            )

            for subm in retval["result"]:
                if len(author := subm["author"]["members"]) > 1:
                    continue

                handle = author[0]["handle"]
                if handle is not None and not self._is_known_user(handle):
                    continue  # Handle must be in the database (foreign key)
                if participants is not None and handle not in participants:
                    continue  # Ensure the author participated in the contest
                if subm["creationTimeSeconds"] > end_time:
                    continue  # Don't accept submissions after the contest has ended

                verdict = (
                    subm["verdict"] if "verdict" in cast(dict, subm).keys() else ""
                )
                problem = subm["problem"]["index"]  # Increases readability
                try:
                    self.cursor.execute(
                        "INSERT INTO codeforces_submission (id, contest_id, creation_time,"
                        "problem, author_handle, programming_language, verdict) VALUES"
                        f'({subm["id"]}, {contest_id}, {subm["creationTimeSeconds"]}, "{problem}",'
                        f'"{handle}", "{subm["programmingLanguage"]}", "{verdict}")'
                    )
                except IntegrityError as e:
                    # print(f"Duplicate submission detected ({subm['id']})...")
                    # print(subm)  # Dump out relevent submission information
                    pass
            self.cnx.commit()  # Commit all data to the database

            if len(retval["result"]) < self.SUBMISSION_BLOCK_SIZE:
                break  # All participant submissions have been recorded
            offset += self.SUBMISSION_BLOCK_SIZE
            if offset % 0x4_000:
                print(f"Processed: {offset}")

    def _fetch_user_submissions(self, contest: int, handle: str) -> None:
        retval = self.api.get_contest_status(contest, handle, count=128)
        assert retval["status"] == "OK", "Invalid API response"
        for subm in retval["result"]:
            verdict = subm["verdict"] if "verdict" in cast(dict, subm).keys() else ""
            problem = subm["problem"]["index"]  # Increases readability
            self.cursor.execute(
                "INSERT INTO codeforces_submission (id, contest_id, creation_time,"
                "problem, author_handle, programming_language, verdict) VALUES"
                f'({subm["id"]}, {contest}, {subm["creationTimeSeconds"]}, "{problem}",'
                f'"{handle}", "{subm["programmingLanguage"]}", "{verdict}")'
            )

    def _fetch_user_info(self, handles: str | Iterable[str], force=False) -> None:
        retval = self.api.get_user_info(handles)
        assert retval["status"] == "OK", f"Invalid API response: {retval['status']}"

        for user in retval["result"]:
            user = cast(dict, user)  # Cast for type checking
            if not force and self._is_known_user(user["handle"]):
                continue  # Don't update the entry if it already exists

            country = user["country"] if "country" in user.keys() else ""
            city = user["city"] if "city" in user.keys() else ""
            rating = user["maxRating"] if "maxRating" in user.keys() else 0
            registered = user["registrationTimeSeconds"]
            query = "INSERT INTO codeforces_user (handle, country, city, max_rating, registered) VALUES (%s, %s, %s, %s, %s)"

            values = (user["handle"], country, city, rating, registered)
            try:
                self.cursor.execute(query, values)  # INSERT INTO [...] VALUES [...]
            except DataError:
                print(f'Invalid author detected ({user["handle"]})...')
        self.cnx.commit()

    def _is_known_user(self, handle: str) -> bool:
        """Used to determine if a user's metadata exists within the database"""
        self.cursor.execute("SELECT * FROM codeforces_user WHERE handle=%s", (handle,))
        return len(self.cursor.fetchall()) > 0

    def _query_contest(self, contest_id: int) -> dict[str, RowItemType] | bool:
        self.cursor.execute(f"SELECT * FROM codeforces_contest WHERE id={contest_id}")
        retval = self.cursor.fetchall()  # assert len(retval) in [0, 1]
        return retval[0] if len(retval) > 0 else False

    def __del__(self):
        # Prevent resource leaks when exiting the program
        self.cursor.close()
        self.cnx.disconnect()


class LeetCodeDatasetBuilder:
    def __init__(self) -> None:
        self.cnx = mysql.connector.connect(user="root", password="root")
        self.cursor = self.cnx.cursor()  # Used for processing queries
        self.cursor.execute("USE horizon_initiative;")
        self.api = LeetCodeAPI()  # Connect to the LeetCode API

    def load_metadata(self, contests: list[int]) -> None:
        pass

    def _fetch_contest_info(
        self, contest_id: int, force=False
    ) -> tuple[int, str, int, int]:
        pass
