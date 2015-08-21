BEGIN;

    ALTER TABLE teams ADD COLUMN onboarding_url text NOT NULL DEFAULT '';
    ALTER TABLE teams ADD COLUMN todo_url text NOT NULL DEFAULT '';

    UPDATE teams
       SET onboarding_url='http://whatcanidoforcoala.org/'
         , todo_url='https://github.com/coala-analyzer/coala/issues'
     WHERE id=81;

    UPDATE teams
       SET onboarding_url='http://tabula.technology/'
         , todo_url='https://github.com/tabulapdf/tabula/issues'
     WHERE id=80;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=79;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/hamperbot/hamper/issues'
     WHERE id=77;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/nim-lang/Nim/issues'
     WHERE id=76;

    UPDATE teams
       SET onboarding_url='https://github.com/magit/magit'
         , todo_url='https://github.com/magit/magit/issues'
     WHERE id=75;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=74;

    UPDATE teams
       SET onboarding_url='https://github.com/feross/webtorrent#ways-to-help'
         , todo_url='https://github.com/feross/webtorrent/issues'
     WHERE id=73;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/scottclowe/matlab-schemer/issues'
     WHERE id=72;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=71;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/zedapp/zed/issues'
     WHERE id=70;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/wout/svg.js/issues'
     WHERE id=69;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=68;

    UPDATE teams
       SET onboarding_url='https://github.com/trakt/Plex-Trakt-Scrobbler#issues'
         , todo_url='https://github.com/trakt/Plex-Trakt-Scrobbler/issues'
     WHERE id=66;

    UPDATE teams
       SET onboarding_url='https://github.com/kilianc/rtail#how-to-contribute'
         , todo_url='https://github.com/kilianc/rtail/issues'
     WHERE id=65;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=64;

    UPDATE teams
       SET onboarding_url='https://dreditor.org/development/contributing'
         , todo_url='https://github.com/unicorn-fail/dreditor/issues'
     WHERE id=63;

    UPDATE teams
       SET onboarding_url='https://github.com/jsbin/jsbin#who-built-this'
         , todo_url='https://github.com/jsbin/jsbin/issues'
     WHERE id=61;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=60;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=59;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=58;

    UPDATE teams
       SET onboarding_url='https://github.com/esdiscuss/esdiscuss.org#contributing'
         , todo_url='https://github.com/esdiscuss/esdiscuss.org/issues'
     WHERE id=57;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=56;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=55;

    UPDATE teams
       SET onboarding_url='https://github.com/Etiene/sailor#contributing'
         , todo_url='https://github.com/Etiene/sailor/issues'
     WHERE id=54;

    UPDATE teams
       SET onboarding_url='https://github.com/anselmh/wdrl/blob/gh-pages/CONTRIBUTING.md'
         , todo_url='https://github.com/anselmh/wdrl/issues'
     WHERE id=53;

    UPDATE teams
       SET onboarding_url='https://github.com/clojure-emacs/cider/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/clojure-emacs/cider/issues'
     WHERE id=52;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=51;

    UPDATE teams
       SET onboarding_url='http://nanoc.ws/contributing/'
         , todo_url='https://github.com/nanoc/nanoc/issues'
     WHERE id=50;

    UPDATE teams
       SET onboarding_url='https://github.com/ucoin-io/ucoin'
         , todo_url='https://github.com/ucoin-io/ucoin/issues'
     WHERE id=49;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/zimme/meteor-active-route/issues'
     WHERE id=48;

    UPDATE teams
       SET onboarding_url='http://community.aegirproject.org/maintainers'
         , todo_url='https://www.drupal.org/project/issues?text=&projects=provision,+hosting,+hostslave,+eldir,+Hostmaster+(Aegir),Hosting+Platform+Pathauto&status=Open&priorities=All&categories=All'
     WHERE id=47;

    UPDATE teams
       SET onboarding_url='https://github.com/toy/image_optim/blob/master/CONTRIBUTING.markdown'
         , todo_url='https://github.com/toy/image_optim/issues'
     WHERE id=46;

    UPDATE teams
       SET onboarding_url='https://github.com/captn3m0/the-joy-of-software-development/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/captn3m0/the-joy-of-software-development/issues'
     WHERE id=44;

    UPDATE teams
       SET onboarding_url='https://github.com/neocities/neocities/issues'
         , todo_url='https://github.com/neocities/neocities/issues'
     WHERE id=43;

    UPDATE teams
       SET onboarding_url='http://wammu.eu/contribute/'
         , todo_url='https://github.com/gammu'
     WHERE id=42;

    UPDATE teams
       SET onboarding_url='http://thecharisproject.org/volunteer/'
         , todo_url=''
     WHERE id=41;

    UPDATE teams
       SET onboarding_url='http://wiki.libravatar.org/contribute/'
         , todo_url='https://bugs.launchpad.net/libravatar'
     WHERE id=40;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=39;

    UPDATE teams
       SET onboarding_url='https://www.freexian.com/services/debian-lts-details.html#join'
         , todo_url=''
     WHERE id=38;

    UPDATE teams
       SET onboarding_url='https://github.com/knop-project/knop'
         , todo_url='https://github.com/knop-project/knop/issues'
     WHERE id=35;

    UPDATE teams
       SET onboarding_url='http://www.sqlalchemy.org/develop.html'
         , todo_url='https://bitbucket.org/zzzeek/sqlalchemy/issues?status=new&status=open'
     WHERE id=34;

    UPDATE teams
       SET onboarding_url='https://github.com/pydoit/doit/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/pydoit/doit/issues'
     WHERE id=33;

    UPDATE teams
       SET onboarding_url='https://github.com/survivejs/webpack_react'
         , todo_url='https://github.com/survivejs/webpack_react/issues'
     WHERE id=32;

    UPDATE teams
       SET onboarding_url='https://github.com/book/Act'
         , todo_url='https://github.com/book/Act/issues'
     WHERE id=31;

    UPDATE teams
       SET onboarding_url='https://github.com/book/CPANio'
         , todo_url='https://github.com/book/CPANio/issues'
     WHERE id=30;

    UPDATE teams
       SET onboarding_url='http://learn.bevry.me/'
         , todo_url=''
     WHERE id=29;

    UPDATE teams
       SET onboarding_url='http://totalism.org/season4'
         , todo_url=''
     WHERE id=28;

    UPDATE teams
       SET onboarding_url='https://github.com/badges/shields/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/badges/shields/issues'
     WHERE id=27;

    UPDATE teams
       SET onboarding_url='https://github.com/cuberite/cuberite/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/cuberite/cuberite/issues'
     WHERE id=26;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=25;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://trello.com/b/KgsuPnPK/encommuns'
     WHERE id=24;

    UPDATE teams
       SET onboarding_url='https://jsonresume.org/team/'
         , todo_url='https://github.com/jsonresume'
     WHERE id=23;

    UPDATE teams
       SET onboarding_url='https://www.drupal.org/project/simplytest'
         , todo_url='https://www.drupal.org/project/issues/simplytest?categories=All'
     WHERE id=22;

    UPDATE teams
       SET onboarding_url='https://github.com/python-pillow/Pillow/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/python-pillow/Pillow/issues'
     WHERE id=21;

    UPDATE teams
       SET onboarding_url='https://github.com/jshttp/style-guide/blob/master/template/Contributing.md'
         , todo_url='https://jshttp.github.io/'
     WHERE id=20;

    UPDATE teams
       SET onboarding_url='https://github.com/Thibaut/devdocs/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/Thibaut/devdocs/issues'
     WHERE id=19;

    UPDATE teams
       SET onboarding_url='https://github.com/nijel/weblate/blob/master/CONTRIBUTING.md'
         , todo_url='https://github.com/nijel/weblate/issues'
     WHERE id=18;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=17;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=16;

    UPDATE teams
       SET onboarding_url='https://github.com/szabgab/Perl-Maven'
         , todo_url='https://github.com/szabgab/Perl-Maven/issues'
     WHERE id=15;

    UPDATE teams
       SET onboarding_url='https://sudoroom.org/wiki/Mesh'
         , todo_url='https://sudoroom.org/wiki/Mesh/ToDos'
     WHERE id=14;

    UPDATE teams
       SET onboarding_url='https://github.com/catapultpgh/main'
         , todo_url='https://github.com/catapultpgh/main/issues'
     WHERE id=13;

    UPDATE teams
       SET onboarding_url=''
         , todo_url=''
     WHERE id=11;

    UPDATE teams
       SET onboarding_url='http://kivy.org/docs/contribute.html'
         , todo_url='https://github.com/kivy/kivy/issues'
     WHERE id=10;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/sindresorhus/pageres/issues'
     WHERE id=9;

    UPDATE teams
       SET onboarding_url='http://www.sublimelinter.com/en/latest/#developer-documentation'
         , todo_url='https://github.com/SublimeLinter/SublimeLinter3/issues'
     WHERE id=8;

    UPDATE teams
       SET onboarding_url='http://mojolicio.us/perldoc/Mojolicious/Guides/Contributing'
         , todo_url='https://github.com/kraih/mojo/issues'
     WHERE id=7;

    UPDATE teams
       SET onboarding_url=''
         , todo_url='https://github.com/kiberpipa'
     WHERE id=6;

    UPDATE teams
       SET onboarding_url='http://tiliado.github.io/nuvolaplayer/development/'
         , todo_url='https://github.com/tiliado'
     WHERE id=5;

    UPDATE teams
       SET onboarding_url='https://sudoroom.org/wiki/Welcome'
         , todo_url='https://sudoroom.org/wiki/Projects'
     WHERE id=4;

    UPDATE teams
       SET onboarding_url='https://byduo.wordpress.com/'
         , todo_url='https://github.com/mixolidia?tab=repositories'
     WHERE id=3;

    UPDATE teams
       SET onboarding_url='https://github.com/ehmatthes/intro_programming'
         , todo_url='https://github.com/ehmatthes/intro_programming/issues'
     WHERE id=2;

    UPDATE teams
       SET onboarding_url='http://inside.gratipay.com/big-picture/welcome'
         , todo_url='https://github.com/issues?q=is%3Aopen+user%3Agratipay'
     WHERE id=1;

END;
