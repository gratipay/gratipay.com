"""
    api_base
    ~~~~~~~~~~~~

    Abstraction for behavior common to other api objects.
"""
from xmlutils import xml_to_dict

class ApiBase(object):
    """
    This object implements behavior common to non-abstract api objects.

    It's basically a mix-in which adds methods to subclasses.
    Most of the methods here are template methods http://en.wikipedia.org/wiki/Template_method_pattern
    """

    def __init__(self):
        self.errors = []

    def _message_block(self, parsed_res):
        """
        Returns the message block from the `parsed_res`
        """
        return parsed_res.get(self.top_xml_key) and parsed_res[self.top_xml_key].get('messages')

    def _check_for_errors(self, parsed_res):
        """
        Checks `parsed_res` for error blocks.
        If it contains error blocks, it return True and sets errors.
        Returns false otherwise.
        """
        error = False
        # Check high level errors.
        if parsed_res.get('error'):
            error = True
            if parsed_res['error'].get('messages') and parsed_res['error']['messages'].get('message'):
                message = parsed_res['error']['messages']['message']
                self.errors = message if isinstance(message, list) else [message]
        return error

    def _check_semantic_errors(self, parsed_res):
        """
        Check request specific error.
        """
        message_block = self._message_block(parsed_res)
        if message_block and message_block.get('message'):
            message = message_block['message']
            if isinstance(message, list):
                error = any(True for m in message
                            if m.get('subclass') == 'error')
            elif isinstance(message, dict):
                error = True if message.get('subclass') == 'error' else False
            if error:
                self.errors = message if isinstance(message, list) else [message]
                self.errors = filter(lambda m: m['subclass']=='error', self.errors)

    def _update_fields(self, xml_res):
        """
        Updates field with the returned `xml_res`.
        """
        parsed_res = xml_to_dict(xml_res)
        if not self._check_for_errors(parsed_res) and parsed_res.get(self.top_xml_key):
            self.__dict__.update(**parsed_res[self.top_xml_key])
            self._check_semantic_errors(parsed_res)

