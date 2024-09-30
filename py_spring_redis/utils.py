import re


def convert_to_snake_case(name: str) -> str:
    """
    Convert a camelCase string to snake_case.
    """
    # Use regex to insert underscores before capital letters
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
