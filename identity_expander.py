"""
Identity Expander Module
------------------------
Provides heuristics for expanding initial OSINT seeds into broader sets of
potential artifacts, usernames, and email addresses.
"""

from string import digits, punctuation, whitespace
from typing import List, Tuple, Dict
import re

# Standard formats for username permutation generation
USR_FORMAT = [
    "{usr_splt[0]}-{usr_splt[1]}",
    "{usr_splt[0]}_{usr_splt[1]}",
    "{usr_splt[0]}.{usr_splt[1]}",
    "{usr_splt[0]}{usr_splt[1]}",
    "{usr_splt[0]}-{usr_splt_stripped[1]}",
    "{usr_splt[0]}_{usr_splt_stripped[1]}",
    "{usr_splt[0]}.{usr_splt_stripped[1]}",
    "{usr_splt[0]}{usr_splt_stripped[1]}",
    "{usr_splt_stripped[0]}-{usr_splt[1]}",
    "{usr_splt_stripped[0]}_{usr_splt[1]}",
    "{usr_splt_stripped[0]}.{usr_splt[1]}",
    "{usr_splt_stripped[0]}{usr_splt[1]}",
]


class ArtifactClassifier:
    """
    Utility class for identifying the type of raw OSINT artifact strings.
    """

    PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "query": r"[a-zA-Z0-9 :._-]+[ :+]+[a-zA-Z0-9 :._-]+",
        "username": r"^[a-zA-Z0-9._-]{3,30}$",
        "url": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
        "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    }

    @staticmethod
    def classify(value: str) -> Tuple[str, str]:
        """
        Classifies an input string into a known artifact type based on regex.

        Args:
            value (str): The raw string to classify.

        Returns:
            Tuple[str, str]: A tuple containing the identified artifact type
                             and the cleaned input value.
        """
        value = value.strip()
        for art_type, pattern in ArtifactClassifier.PATTERNS.items():
            if re.search(pattern, value):
                return art_type, value
        return "other", value


class IdentityExpander:
    """
    Generates permutations of identities to expand the search surface.
    """

    @staticmethod
    def generate_username_permutations(base: str) -> List[Dict[str, str]]:
        """
        Generates common username permutations for a given base handle.

        Args:
            base (str): The base username to expand.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each containing 'type' and 'value'.
        """
        usernames = set(
            {
                base,
                base.strip(),
                base.strip(whitespace + digits),
                base.strip(punctuation + digits + whitespace),
            }
        )
        username_lists = [
            set(base.strip(punctuation + whitespace).split(symbol))
            for symbol in punctuation
        ]
        for user in username_lists:
            if "" in user:
                user.remove("")
        username_lists = list(list(lst) for lst in username_lists)

        def append_user_lists(user_lists):
            for usr_splt in user_lists:
                if len(usr_splt) < 2:
                    continue
                for formatter in USR_FORMAT:
                    username = formatter.format(
                        usr_splt=usr_splt,
                        usr_splt_stripped=[
                            usr_splt[0].strip(digits),
                            usr_splt[1].strip(digits),
                        ],
                    )
                    usernames.add(username.strip("-_.="))

        append_user_lists(username_lists)
        for lst in username_lists:
            lst.reverse()
        append_user_lists(username_lists)
        return list({"type": "username", "value": usn} for usn in usernames)

    @staticmethod
    def generate_name_permutations(fullname: str) -> List[Dict[str, str]]:
        """
        Generates username and email address permutations from a full name.

        Args:
            fullname (str): The subject's full name.

        Returns:
            List[Dict[str, str]]: A list of potential identity artifacts.
        """
        if not fullname or " " not in fullname:
            return []

        parts = fullname.lower().split()
        fname, lname = parts[0], parts[-1]

        return [
            {"type": "username", "value": f"{fname}{lname}"},
            {"type": "username", "value": f"{fname}.{lname}"},
            {"type": "username", "value": f"{fname}_{lname}"},
            {"type": "username", "value": f"{lname}_{fname}"},
            {"type": "username", "value": f"{lname}{fname}"},
            {"type": "username", "value": f"{lname}.{fname}"},
            {"type": "email", "value": f"{fname}{lname}@gmail.com"},
            {"type": "email", "value": f"{fname}.{lname}@gmail.com"},
            {"type": "email", "value": f"{fname}_{lname}@gmail.com"},
            {"type": "email", "value": f"{lname}_{fname}@gmail.com"},
            {"type": "email", "value": f"{lname}{fname}@gmail.com"},
            {"type": "email", "value": f"{lname}.{fname}@gmail.com"},
            {"type": "email", "value": f"{fname}{lname}@hotmail.com"},
            {"type": "email", "value": f"{fname}.{lname}@hotmail.com"},
            {"type": "email", "value": f"{fname}_{lname}@hotmail.com"},
            {"type": "email", "value": f"{lname}_{fname}@hotmail.com"},
            {"type": "email", "value": f"{lname}{fname}@hotmail.com"},
            {"type": "email", "value": f"{lname}.{fname}@hotmail.com"},
            {"type": "username", "value": f"{fname}_{lname[:6]}"},
            {"type": "username", "value": f"{lname[:6]}_{fname}"},
            {"type": "username", "value": f"{lname[:6]}_{fname[:6]}"},
            {"type": "username", "value": f"{fname[:6]}_{lname[:6]}"},
            {"type": "username", "value": f"{fname[:6]}_{lname}"},
            {"type": "username", "value": f"{fname}{lname[:6]}"},
            {"type": "username", "value": f"{lname[:6]}{fname}"},
            {"type": "username", "value": f"{lname[:6]}{fname[:6]}"},
            {"type": "username", "value": f"{fname[:6]}{lname[:6]}"},
            {"type": "username", "value": f"{fname[:6]}_{lname}"},
        ]
