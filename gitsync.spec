%define alphatag 20120102

Name:           gitsync
Version:        0.0.1
Release:        0.1.%{alphatag}git%{?dist}
Summary:        Automated git-based synchronization

License:        GPLv3+
URL:            http://ambre.pingoured.fr/cgit/gitsync.git
# The source was pulled from upstreams git scm. Use the following
# commands to generate the tarball
# git clone http://ambre.pingoured.fr/cgit/gitsync.git
# cd gitsync && git archive --format=tar --prefix=gitsync-0.0.1/ fd39ef44ed57a4ede4f586a852598479efa9db13 > ../gitsync-20120102.tar.bz2
Source0:        gitsync-%{alphatag}.tar.bz2

Requires:       git
Requires:       python

BuildArch:      noarch
BuildRequires:  python-devel


%description
Automated git-based synchronization.
Embedded in a scheduler (such as cron) it watchs the content of a
folder and add/remove/commit the changes which are made there.

This way it kind of provide a similar service then dropbox or
sparkleshare but:
- in python (no mono-pile to install)
- in cron (set your frequency as desired)
- in git (get real track changes).

%prep
%setup -q


%build
#emtpy build


%install
rm -rf %{buildroot}
mkdir -p  %{buildroot}%{_bindir}
install -m 755 %{name}.py %{buildroot}%{_bindir}/%{name}

 
%files
%doc README LICENSE
%{_bindir}/%{name}


%changelog
* Mon Jan 02 2012 Johan Cwiklinski <johan AT x-tnd DOT be> - 0.0.1-0.1.20120102git
- First SPEC draft
