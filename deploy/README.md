Deployment hooks go here, in the `./deploy/` directory. The run order is:

1. `before.sql`
1. `after.py`
1. `after.sql`

All three steps are optional. During
[`deploy.sh`](https://github.com/gratipay/gratipay.com/blob/master/deploy.sh)
we push new code to Heroku between (1) and (2); that's what "before" and
"after" refer to. There is no `before.py` because that would have to run in an
old dyno, which would be hard to simulate during development. Hopefully you can
get done what you need to get done in `after.py`? Note that you can make db
calls from inside `after.py` for additional flexibility:

```python
from gratipay import wireup

db = wireup.db(wireup.env())
db.run("CREATE TABLE foo")
```


## Development

To include database changes with a pull request, simply make new hook files in
this directory on your PR branch. They'll be automatically removed after being
applied in `deploy.sh`. To initialize your local database, including applying
the deploy hooks, use these make targets:

- `make schema` — hits `DATABASE_URL` per `defaults.env` and `local.env`
- `make test-schema` — hits `DATABASE_URL` per `defaults.env`, `local.env`,
  `tests/defaults.env`, and `tests/local.env`

You'll find logfiles at `./make-{test-,}schema.log` to help you debug.


## Testing

Put tests for your deploy hooks in `deploy/tests.py` on your PR branch. The
test suite will include this file, and `deploy.sh` will remove it. There is a
`DeployHooksHarness` in `gratipay.testing` with a `run_deploy_hooks` method
that runs the deploy hooks. Here's a stub test file:

```python
from gratipay.testing import DeployHooksHarness


class Tests(DeployHooksHarness):

    def test_it_works(self):
        assert before_state 
        self.run_deploy_hooks()
        assert after_state 
```
