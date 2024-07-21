ZSH
=========

Installs zsh and the oh-my-zsh framework for root and a number of set users.


Role Variables
--------------
| Name          | Type         | Default | Required | Description                                  |
|---------------|--------------|---------|----------|----------------------------------------------|
| `omz_url`     | String       | -       | no       | The url to download the omz install script.  |
| `omz_aliases` | List(String) | -       | no       | A list of aliases to add to the .zshrc file. |

Dependencies
------------

A list of other roles hosted on Galaxy should go here, plus any details in regards to parameters that may need to be set for other roles, or variables that are used from other roles.

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: username.rolename, x: 42 }

License
-------

BSD

Author Information
------------------

An optional section for the role authors to include contact information, or a website (HTML is not allowed).
