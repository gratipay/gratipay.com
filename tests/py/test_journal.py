from gratipay.journal import Journal


def test_journal_can_be_instantiated():
    assert Journal().__class__.__name__ == 'Journal'

