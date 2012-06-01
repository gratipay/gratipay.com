"""
    xmldict
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Convert xml to python dictionaries.
"""
import datetime

elems_preserving_attributes = [ 'message' ]

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
    return _to_xml(dict_xml)

# Functions below this line are implementation details.
# Unless you are changing code, don't bother reading.
# The functions above constitute the user interface.

def _to_xml(el):
    """
    Converts `el` to its xml representation.
    """
    val = None
    if isinstance(el, dict):
        val = _dict_to_xml(el)
    elif isinstance(el, bool):
        val = str(el).lower()
    else:
        val = el
    return val

def _dict_to_xml(els):
    """
    Converts `els` which is a python dict to corresponding xml.
    """
    tags = []
    for tag, content in els.iteritems():
        if isinstance(content, list):
            for el in content:
                tags.append('<%s>%s</%s>' % (tag, _to_xml(el), tag))
        else:
            tags.append('<%s>%s</%s>' % (tag, _to_xml(content), tag))
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

def _str_to_datetime(date_str):
    try:
        val = datetime.datetime.strptime(date_str,  "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        val = date_str
    return val

def _str_to_boolean(bool_str):
    if bool_str.lower() != 'false' and bool(bool_str):
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
        if el.tag in elems_preserving_attributes:
            val = dict(attribs)
            if el.text: val['text'] = el.text
        elif el.text:
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
    'boolean': _str_to_boolean,
    'datetime': _str_to_datetime,
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
