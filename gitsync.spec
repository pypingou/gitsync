Name:               gitsync
Version:            1.0.2
Release:            1%{?dist}
Summary:            Automated git-based synchronization

License:            GPLv3+
URL:                https://github.com/pypingou/gitsync
# The source was pulled from upstreams git scm. Use the following
# commands to generate the tarball
# git clone http://ambre.pingoured.fr/cgit/gitsync.git
# cd gitsync && git archive --format=tar --prefix=gitsync-0.0.1/ fd39ef44ed57a4ede4f586a852598479efa9db13 > ../gitsync-20120102.tar.bz2
Source0:            gitsync-1.0.1.tar.bz2

BuildArch:          noarch

BuildRequires:      python2-devel
BuildRequires:      systemd-devel

Requires:           python2-pygit2
Requires:           python2-watchdog
Requires(post):     systemd
Requires(preun):    systemd
Requires(postun):   systemd


%description
Automated git-based synchronization.
Embedded in a scheduler (such as cron) it watchs the content of a
folder and add/remove/commit the changes which are made there.

This way it kind of provide a similar service then dropbox or
sparkleshare but:
- in python (no mono-pile to install)
- in cron (set your frequency as desired) or in daemon mode (watches the
  changes in the file-system and commit as needed)
- in git (get real track changes).

%prep
%setup -q


%build
#emtpy build


%install
rm -rf %{buildroot}
mkdir -p  %{buildroot}%{_bindir}
install -m 755 %{name}.py %{buildroot}%{_bindir}/%{name}

mkdir -p $RPM_BUILD_ROOT/%{_unitdir}
install -m 644 gitsync.service \
    $RPM_BUILD_ROOT/%{_unitdir}/gitsync.service

%post
%systemd_post gitsync.service
%preun
%systemd_preun gitsync.service
%postun
%systemd_postun_with_restart gitsync.service


%files
%doc README LICENSE
%{_bindir}/%{name}
%{_unitdir}/gitsync.service


%changelog
* Wed Jan 04 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0.2-1
- Update to 1.0.2
- Fix the daemon mode when watching a folder where a file is deleted

* Wed Jan 04 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0.1-1
- Update to 1.0.1

* Fri April 18 2014 Pierre-Yves Chibon <pingou AT pingoured DOT fr> - 0.0.2-0.1.20140418git
- Bump to a 0.0.2 release
- Add dependency to python-watchdog and python-pygit2

* Tue Jan 03 2012 Pierre-Yves Chibon <pingou AT pingoured DOT fr> - 0.0.1-0.2.20120102git
- Fix the Requires of the spec (to GitPython which will bring git and python)

* Mon Jan 02 2012 Johan Cwiklinski <johan AT x-tnd DOT be> - 0.0.1-0.1.20120102git
- First SPEC draft
