# Necessary to use the prebuilt qtbindings. Without this, the RPATHs being
# wrong, the shared libraries can't find each other
Autoproj.env_add_path(
    'LD_LIBRARY_PATH',
    '/home/buildbot/.local/share/autoproj/gems/ruby/2.5.0/gems/qtbindings-4.8.6.5-x86_64-linux/lib/2.5'
)
                      
