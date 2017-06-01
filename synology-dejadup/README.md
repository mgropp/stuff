Synology and Déjà Dup
=====================

Here is how I got a Synology Disk Station (DSM 6) to work with Déjà Dup.


Public Key Authentication
-------------------------
Public key authentication needs to be enabled explicitly in DSM's
`/etc/ssh/sshd_config`:

```
PubkeyAuthentication yes
```

While you're at it, make sure `sshd` will process your `~/.ssh/authorized_keys`
file:

```
AuthorizedKeysFile .ssh/authorized_keys
```

And if you want to, you can also disable password authentication for your
backup user here.

When you're done, reload the service:

```
synoservicectl --reload sshd
```

Note:
I had some trouble with DSM resetting the login shell of my backup account
to `nologin` --- check this if you're suddenly running into
"permission denied" problems.


rsync and SFTP
--------------

Déjà Dup uses both SFTP and rsync.

Unfortunately Synology ships two different versions of `rsync`, one in
`/bin` and another one in `/usr/bin`. The one I found in my `/usr/bin` doesn't
support public keys, and it is, of course, the default.
(Probably, this `rsync` uses the settings you can make in the GUI.)

Now, if you had a good look at your `sshd_config` before, you may have seen why:

```
# This sshd was compiled with PATH=/usr/bin:/bin:/usr/sbin:/sbin
```

I tried to override this by setting the environment in the SSHD configuration
and in PAM, but neither worked.

My solution:
Force the correct `rsync` to be run in the `authorized_keys` file,
using the `command=…` directive.

This raises two new problems, however:

  1) We need to allow `rsync`, `sftp-server`, and possibly `scp`, not just
     a single command.
     
     This can be fixed easily with a wrapper script.
  
  2) Synology uses OpenSSH's `internal-sftp` SFTP server, and doesn't even
     ship an external `sftp-server` binary. And we can't call the internal
     server from the wrapper script.
     
     So we need to install an SFTP server.
     I used Easy Bootstrap Installer to install Entware, and then
     ran `/opt/bin/opkg` to install the `openssh-sftp-server` package.
     
     Now if we see the `internal-sftp` command in the wrapper script,
     we just execute `/opt/libexec/sftp-server` instead.
     (I wanted to keep `internal-sftp` for the other users, so I didn't change
     the global settings in `sshd_config`.)
     
Done.
