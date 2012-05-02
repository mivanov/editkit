Settings
========

Administration interface
------------------------

EditKit comes with a web-based admin interface.  If EditKit is running on
your machine, it can be found at ``http://localhost/admin/``.  Otherwise,
you can find the admin interface at ``http://<your server's address>/admin/``

.. figure:: /_static/images/admin_login.png

At the prompt, enter your superuser login and password.  If you don't
have a superuser login and password, you can create one by running
``sudo editkit-manage createsuperuser``.

When you login, you will see all of the object types that you can modify on the
left, and a list of recent actions done by administrators on the right(if any).

.. figure:: /_static/images/admin_home.png



Domain name and site name
-------------------------

In the admin interface, go to "Sites", click on the site you want to modify,
enter the domain name and display name and press "Save".

.. figure:: /_static/images/admin_site.png


``localsettings.py``
--------------------

Settings particular to your installation go in this file, found at 
``/usr/share/editkit/conf/localsettings.py`` on your system. Here are some
things you may need or wish to modify:

``SITE_THEME``
    The name of the directory under ``themes`` to look for the theme templates
    and static files.  We'll have more detail on creating a theme soon.

``EMBED_ALLOWED_URLS``
    This is a list of regular expressions used to restrict what kinds of
    content users can embed.  If an embedded URL does not pass any of the
    regular expressions in this list, it will not be shown.

After changing settings you'll need to restart Apache.  On most systems
you can do this by running ``sudo /etc/init.d/apache2 restart``.
