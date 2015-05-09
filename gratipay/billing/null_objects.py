class NullCard:
    def __init__(self, *args, **kwargs):
        return None

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, mname):
        return self

    def __nonzero__(self):
        return False

    def __unicode__(self):
        return u''
