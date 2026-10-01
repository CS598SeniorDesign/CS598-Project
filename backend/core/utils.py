from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element


def get_attribute_value(element: Element, xpath: str) -> str | None:
    """
    Safely finds a sub-element by XPath and returns its "value" attribute.

    :param element: The XML element to search within.
    :type element: xml.etree.ElementTree.Element
    :param xpath: The XPath expression used to locate the sub-element.
    :type xpath: str
    :returns: The string content of the "value" attribute if the node exists, otherwise None.
    :rtype: str | None
    """

    attribute = "value"
    default = None

    node = element.find(xpath)
    return node.attrib.get(attribute) if node is not None else default


def get_attribute(element: Element, xpath: str, attribute: str) -> str | None:
    """
    Safely finds a sub-element by XPath and returns the specified attribute.

    :param element: The XML element to search within.
    :type element: xml.etree.ElementTree.Element
    :param xpath: The XPath expression used to locate the sub-element.
    :type xpath: str
    :param attribute: The name of the attribute to retrieve from the located node.
    :type attribute: str
    :returns: The string content of the requested attribute if the node exists, otherwise None.
    :rtype: str | None
    """

    default = None

    node = element.find(xpath)
    return node.attrib.get(attribute) if node is not None else default


def parse_optional_integer(raw_value: str | None) -> int | None:
    """
    Converts an XML attribute value to an integer, returning None when it is missing or not a whole number.

    :param raw_value: The raw attribute string, or None if the attribute was absent.
    :type raw_value: str | None
    :returns: The parsed integer, or None if the value is missing or malformed.
    :rtype: int | None
    """

    if raw_value is None:
        return None

    try:
        return int(raw_value)
    except ValueError:
        return None


def parse_optional_float(raw_value: str | None) -> float | None:
    """
    Converts an XML attribute value to a float, returning None when it is missing or not a finite number.

    BGG uses both an empty string and the literal text "null" for values that were never recorded (for example, a
    player's score), so neither may be treated as zero.

    :param raw_value: The raw attribute string, or None if the attribute was absent.
    :type raw_value: str | None
    :returns: The parsed float, or None if the value is missing, malformed, infinite, or NaN.
    :rtype: float | None
    """

    if raw_value is None:
        return None

    try:
        parsed_value = float(raw_value)
    except ValueError:
        return None

    return parsed_value if math.isfinite(parsed_value) else None
