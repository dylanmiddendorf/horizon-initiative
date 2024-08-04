from bs4 import BeautifulSoup

import http.client  # Low level HTTP client
import json  # Manages REST API responses
import re  # Regular expression

from typing import Iterable


# TODO Standardize API responses (in some fashion)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
)


class CodeforcesAPI:
    BASE_URL = "codeforces.com"
    BASE_HEADERS = {"User-Agent": USER_AGENT}

    def __init__(self) -> None:
        self.client = http.client.HTTPSConnection(host=CodeforcesAPI.BASE_URL)

        # Obtain the `JSESSIONID` to authorize further requests
        self.BASE_HEADERS.update(self._get_session_headers())

    def _get_session_headers(self):
        self.client.request("GET", "/", headers={"X-CSRF-Token": "fetch"})
        response = self.client.getresponse()

        soup = BeautifulSoup(response, "html.parser")
        token = soup.find("meta", attrs={"name": "X-Csrf-Token"})

        if not token:  # The X-Csrf-Token is required to scrape the submissions
            raise ValueError("Unable to find X-Csrf-Token")

        for cookie in response.getheader("Set-Cookie").split(";"):
            if re.match("^JSESSIONID=([0-9A-F]+)$", cookie):
                return ("X-Csrf-Token", token["content"]), ("Cookie", cookie)

        raise ValueError("Unable to find JSESSIONID in response headers")

    def _query_endpoint(
        self, method: str, endpoint: str, body: str = None, headers: dict[str, str] = {}
    ) -> dict:
        headers = {**CodeforcesAPI.BASE_HEADERS, **headers}
        self.client.request(method, endpoint, body, headers=headers)
        response = self.client.getresponse()

        if response.status != 200:
            raise ValueError(f"Invalid HTTP status recived: {response.status}")

        api_response = json.load(response)
        assert api_response["status"] == "OK"
        return api_response

    def get_contest_standings(
        self, contest_id: int, offset: int = 1, count: int = 25, show_unoffical=False
    ) -> dict:
        """Returns the description of the contest and the requested part of the standings.

        Args:
            contest_id: The unique identifier of the contest (not the round
            number).
            offset: 1-based index of the first standings row to include in the
            returned list.
            count: Number of standings rows to retrieve.
            show_unoffical: Determines whether to include unofficial
            participants (virtual, out of competition) in the standings.

        Returns:
            Returns an object with two fields:
            - "status": HTTP status message.
            - "result": Contains contest and problem information along with the requested participant standings.

            Example result:
            .. code-block:: json
            {
                "status": "OK",
                "result": {
                    "contest": {...},
                    "problems": [...],
                    "rows": [...]
                }
            }
        """
        parameters = f"contestId={contest_id}&from={offset}&count={count}&showUnofficial={show_unoffical}"
        endpoint = "/api/contest.standings?" + parameters
        return self._query_endpoint("GET", endpoint)

    def get_contest_status(
        self, contest_id: int, handle: str = None, offset: int = 1, count: int = 25
    ) -> dict:
        """Returns submissions for specified contest. Optionally can return submissions of specified user.

        Args:
            contest_id: The unique identifier of the contest (not the round number).
            handle: The Codeforces user handle.
            offset: 1-based index of the first standings row to include in the returned list.
            count: Number of standings rows to retrieve.

        Returns:
            Returns an object with two fields:
            - "status": HTTP status message.
            - "result": A list of submission objects, sorted in decreasing order of submission id.

            Example result:
            .. code-block:: json
            {
                "status": "OK",
                "results": [...]
            }
        """
        parameters = f"contestId={contest_id}&from={offset}&count={count}"
        if handle is not None:  # Ensure the parameter has a value
            parameters += f"&handle={handle}"

        endpoint = "/api/contest.status?" + parameters
        return self._query_endpoint("GET", endpoint)

    def get_user_info(self, handles: str | Iterable[str]) -> dict:
        if isinstance(handles, str):
            handles = (handles,)  # Prepare handles for the endpoint curation
        endpoint = f"/api/user.info?handles={';'.join(handles)}"
        return self._query_endpoint("GET", endpoint)

    def get_submission(self, contest_id: int, submission_id: int) -> dict:
        body = f"submissionId={submission_id}"  # Requires body because of POST request
        headers = {
            "Referer": f"https://codeforces.com/contest/{contest_id}/standings",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        return self._query_endpoint("POST", "/data/submitSource", body, headers)


class LeetCodeAPI:
    BASE_URL = "leetcode.com"
    BASE_HEADERS = {"User-Agent": USER_AGENT}

    def __init__(self) -> None:
        self.client = http.client.HTTPSConnection(host=LeetCodeAPI.BASE_URL)

    def _query_endpoint(self, endpoint: str, headers: dict[str, str] = {}) -> dict:
        headers = {**LeetCodeAPI.BASE_HEADERS, **headers}
        self.client.request("GET", endpoint, headers=headers)
        response = self.client.getresponse()

        assert response.status == 200
        return json.load(response)

    def get_contest_info(self, contest_slug: str) -> dict:
        """Returns general information about specified contest.

        Args:
            contest_slug: The slug of the contest's title.

        Returns:
            Returns an object with six fields:
            - "contest": Information about the contest.
            - "problems": The problem set used in the contest.
            - "containsPremium": Indicates if the contest contains premium problems.
            - "registered": Indicates if the user is registered for the contest.
            - "survey": Any survey associated with the contest.
            - "current_timestamp": The current UNIX timestamp.

            Example result:
            .. code-block:: json
            {
                "contest": {...},
                "problems": [...],
                "containsPremium": false,
                "registered": false,
                "survey": null,
                "current_timestamp": 0
            }
        """
        return self._query_endpoint(f"/contest/api/info/{contest_slug}/")

    def get_contest_ranking(self, contest_slug: str, page: int = 1) -> dict:
        """Returns the ranking information for a specified contest.

        Args:
            contest_slug: The slug of the contest's title.
            page: The page number of the rankings to retrieve. Each page
            contains results for 25 contestants. Defaults to 1.

        Returns:
            Returns an object with five fields:
            - is_past: Whether the contest has concluded.
            - submissions: A list of dictionaries containing details about user's submission.
            - questions: The problem set used in the contest.
            - total_rank: A list containing the associated participant rankings.
            - user_num: The total number of users who participated in the contest.

            Example result:
            .. code-block:: json
            {
                "is_past": false,
                "submissions": [...],
                "questions": [...],
                "total_rank": [...],
                "user_num": 0
            }

        Raises:
            ValueError: If `page` is less than 1.
        """

        if page < 1:  # Quickly verify that page is in the correct domain
            raise ValueError("page must be a positive integer")
        endpoint = f"/contest/api/ranking/{contest_slug}/?pagination={page}"
        return self._query_endpoint(endpoint)

    def get_submission(self, submission_id: int) -> dict:
        """Returns the specified submission's source code.

        Args:
            submission_id: The unique submission id.

        Returns:
            Returns an object with four fields:
            - "id": The unique identifier for the submission.
            - "code": The source code of the submission.
            - "lang": The programming language used for the submission.
            - "contest_submission": N/A.

            Example result:
            .. code-block:: json
            {
                "id": 0,
                "code": "<source-code>",
                "lang": "<lang>",
                "contest_submission": 0
            }
        """
        return self._query_endpoint(f"/api/submissions/{submission_id}/")
