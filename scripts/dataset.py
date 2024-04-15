from api import CodeforcesAPI, LeetCodeAPI
import mysql.connector

import json
from typing import cast


CODEFORCES_BLOCK_SIZE = 128


class CodeforcesDatasetBuilder:
    def __init__(self) -> None:
        self.cnx = mysql.connector.connect(user="root", password="root")
        self.cursor = self.cnx.cursor()  # Used for processing queries
        self.cursor.execute("USE horizon_initiative;")
        self.api = CodeforcesAPI()  # Connect to the codeforces API

    def load_metadata(self, contests: list[int]) -> None:
        for contest in contests:
            retval = self.api.get_contest_standings(contest, count=1)
            assert retval["status"] == "OK", f"Invalid API response: {retval['status']}"
            contest_standings = retval["result"]

            self.cursor.execute(f"SELECT * FROM codeforces_contest WHERE id={contest}")
            if len(self.cursor.fetchall()) == 0:
                contest_name = contest_standings["contest"]["name"]
                contest_start_time = contest_standings["contest"]["startTimeSeconds"]
                query = "INSERT INTO codeforces_contest (id, name, start_time) VALUES (%s, %s, %s)"
                values = (contest, contest_name, contest_start_time)
                self.cursor.execute(query, values)  # INSERT INTO [...] VALUES [...]

            self._fetch_contest_standings(contest)

    def _fetch_contest_standings(self, contest_id: int):
        offset = 1  # Used to store the last row fetched
        while True:
            print(f"Fetching user {offset} to {offset + 128}...")
            retval = self.api.get_contest_standings(contest_id, offset, 128)
            assert retval["status"] == "OK", f"Invalid API response: {retval['status']}"
            contest_standings = retval["result"]

            for row in contest_standings["rows"]:
                party_memebers = row["party"]["members"]
                assert len(party_memebers) == 1, "Submission MUST contain one author"
                self._fetch_user_submissions(contest_id, party_memebers[0]["handle"])
                self.cnx.commit()  # Commit all data to the database

            if len(contest_standings["rows"]) < 128:
                break  # All participant submissions have been recorded
            offset += 128

    def _fetch_user_info(self, handle: str) -> None:
        retval = self.api.get_user_info(handle)
        assert retval["status"] == "OK", f"Invalid API response: {retval['status']}"
        user = cast(dict, retval["result"][0])  # Increase readability

        country = user["country"] if "country" in user.keys() else ""
        city = user["city"] if "city" in user.keys() else ""
        rating, registered = user["maxRating"], user["registrationTimeSeconds"]
        query = "INSERT INTO codeforces_user (handle, country, city, max_rating, registered) VALUES (%s, %s, %s, %s, %s)"
        values = (handle, country, city, rating, registered)
        self.cursor.execute(query, values)  # INSERT INTO [...] VALUES [...]

    def _fetch_user_submissions(self, contest: int, handle: str) -> None:
        self.cursor.execute("SELECT * FROM codeforces_user WHERE handle=%s", (handle,))
        if len(self.cursor.fetchall()) == 0:
            self._fetch_user_info(handle)

        retval = self.api.get_contest_status(contest, handle, count=128)
        assert retval["status"] == "OK", "Invalid API response"
        for subm in retval["result"]:
            verdict = subm["verdict"] if "verdict" in cast(dict, subm).keys() else ""
            problem = subm["problem"]["index"]  # Increases readability
            self.cursor.execute(
                "INSERT INTO codeforces_submission (id, contest_id, creation_time,"
                f"problem, author_handle, programming_language, verdict) VALUES"
                f"({subm['id']}, {contest}, {subm['creationTimeSeconds']},"
                f"\"{problem}\", \"{handle}\", \"{subm['programmingLanguage']}\", \"{verdict}\")"
            )
