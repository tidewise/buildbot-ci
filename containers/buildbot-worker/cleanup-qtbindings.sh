gem_root=/home/buildbot/.local/share/autoproj/gems/ruby/2.5.0/gems
rm -rf $gem_root/qtbindings*/ext/build

for i in $gem_root/qtbindings*/lib/2.5/*.so*; do
    if test -f $i.0.0; then
        ln -sf $i.0.0 $i
    elif test -f $i.?.0.0; then
        ln -sf $i.?.0.0 $i
    fi
done
strip $gem_root/qtbindings*/lib/2.5/*.so*
