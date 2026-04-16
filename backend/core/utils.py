from __future__ import annotations

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
    Safely finds a sub-element by XPath and returns the given attribute attribute.

    :param element: The XML element to search within.
    :type element: xml.etree.ElementTree.Element
    :param xpath: The XPath expression used to locate the sub-element.
    :type xpath: str
    :returns: The string content of the given attribute if the node exists, otherwise None.
    :rtype: str | None
    """

    default = None

    node = element.find(xpath)
    return node.attrib.get(attribute) if node is not None else default
