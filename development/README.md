# Gittip Development Environment

Gittip aims to provide multiplatform support for development via
Vagrant.

## Requirements

While not specifically required, the indicated versions have been vetted
as working.

  * [Virtualbox 4.3.8](https://www.virtualbox.org/wiki/Downloads)
  * [Vagrant 1.4.3](https://www.vagrantup.com/downloads.html)

_**Linux users note:** the package repository versions of Vagrant are
frequently out-of-date. Please use the official link above._

## First-time setup

You should only need to run these commands once, when you first start
using this Vagrant environment.

```
vagrant plugin install vagrant-omnibus
vagrant plugin install vagrant-librarian-chef
```

## Usage

```
cd development
vagrant up
vagrant ssH -c "sudo -iu postgres make run"
```

You now have the site running at `http://localhost:8537`. Huzzah!

## Recommended plugins

While not strictly necessary, they will make working with Vagrant a bit
simpler and/or standardized.

  * [vagrant-cachier]() plugin: `vagrant plugin install vagrant-cachier`
