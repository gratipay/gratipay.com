"""
    Methods to work with XML.
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""
import datetime
from utils import str_to_datetime, str_to_boolean

def xml_to_dict(root_or_str):
    """
    Converts `root_or_str` which can be parsed xml or a xml string to dict.

    """
    root = root_or_str
    if isinstance(root, str):
        import xml.etree.cElementTree as ElementTree
        root = ElementTree.XML(root_or_str)
    return {root.tag: _from_xml(root)}

def dict_to_xml(dict_xml):
    """
    Converts `dict_xml` which is a python dict to corresponding xml.
    """
    return _xml_from_dict(dict_xml)

# Functions below this line are implementation details.
# Unless you are changing code, don't bother reading.
# The functions above constitute the user interface.

def _to_xml(tag, content):
    if isinstance(content, dict):
        val = '<%(tag)s>%(content)s</%(tag)s>' % dict(tag=tag,
                                                      content=_xml_from_dict(content))
    elif isinstance(content, bool):
        val = '<%(tag)s>%(content)s</%(tag)s>' % dict(tag=tag, content=str(content).lower())
    else:
        val = '<%(tag)s>%(content)s</%(tag)s>' % dict(tag=tag, content=content)
    return val

def _xml_from_dict(dict_xml):
    """
    Converts `dict_xml` which is a python dict to corresponding xml.
    """
    tags = []
    for tag, content in dict_xml.iteritems():
        tags.append(_to_xml(tag, content))
    return ''.join(tags)

def _is_xml_el_dict(el):
    """
    Returns true if `el` is supposed to be a dict.
    This function makes sense only in the context of making dicts out of xml.
    """
    if len(el) == 1  or el[0].tag != el[1].tag:
        return True
    return False

def _is_xml_el_list(el):
    """
    Returns true if `el` is supposed to be a list.
    This function makes sense only in the context of making lists out of xml.
    """
    if len(el) > 1 and el[0].tag == el[1].tag:
        return True
    return False

def _from_xml(el):
    """
    Extracts value of xml element element `el`.
    """
    val = None
    # Parent node.
    if el:
        if _is_xml_el_dict(el):
            val = _dict_from_xml(el)
        elif _is_xml_el_list(el):
            val = _list_from_xml(el)
    # Simple node.
    else:
        attribs = el.items()
        # An element with no subelements but text.
        if el.text:
            val = _val_and_maybe_convert(el)
        # An element with attributes.
        elif attribs:
            val = dict(attribs)
    return val

def _val_and_maybe_convert(el):
    """
    Converts `el.text` if `el` has attribute `type` with valid value.
    """
    text = el.text.strip()
    data_type = el.get('type')
    convertor = _val_and_maybe_convert.convertors.get(data_type)
    if convertor:
        return convertor(text)
    else:
        return text
_val_and_maybe_convert.convertors = {
    'boolean': str_to_boolean,
    'datetime': str_to_datetime,
    'integer': int
}

def _list_from_xml(els):
    """
    Converts xml elements list `el_list` to a python list.
    """
    res = []
    tag = els[0].tag
    for el in els:
        res.append(_from_xml(el))
    return {tag: res}

def _dict_from_xml(els):
    """
    Converts xml doc with root `root` to a python dict.
    """
    # An element with subelements.
    res = {}
    for el in els:
        res[el.tag] = _from_xml(el)
    return res
