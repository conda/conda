# Copyright © 2015-2018 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

TAR = tar
tar = $(TAR) -P --owner root --group root --mode a+rX

.PHONY: all
all:

.PHONY: clean
clean:
	rm -rf *.tar tmp* moo* cur* par*

all: absolute1.tar
absolute1.tar:
	echo moo > moo
	$(tar) -cf $(@) --transform s,^,/tmp/, moo
	rm -f moo

all: absolute2.tar
absolute2.tar:
	echo moo > moo
	$(tar) -cf $(@) --transform s,^,//tmp/, moo
	rm -f moo

all: relative0.tar
relative0.tar:
	echo moo > moo
	$(tar) -cf $(@) --transform s,^,../, moo
	rm -f moo

all: relative2.tar
relative2.tar:
	echo moo > moo
	$(tar) -cf $(@) --transform s,^,tmp/../../, moo
	rm -f moo

all: symlink.tar
symlink.tar:
	ln -sf /tmp/moo moo
	$(tar) -cf $(@) moo
	rm -f moo
	echo moo > moo
	$(tar) -rf $(@) moo
	rm -f moo

all: dirsymlink.tar
dirsymlink.tar:
	ln -sf /tmp tmp
	$(tar) -cf $(@) tmp
	rm -f tmp
	mkdir -m 755 tmp
	echo moo > tmp/moo
	$(tar) -rf $(@) tmp/moo
	rm -rf tmp

all: dirsymlink2a.tar
dirsymlink2a.tar:
	ln -sf . cur
	ln -sf cur/.. par
	$(tar) -cf $(@) cur par
	rm -f cur par
	mkdir -m 755 par
	echo moo > par/moo
	$(tar) -rf $(@) par/moo
	rm -rf par

all: dirsymlink2b.tar
dirsymlink2b.tar:
	ln -sf . cur
	ln -sf .. par
	$(tar) -cf $(@) cur cur/par
	rm -f cur par
	mkdir -m 755 par
	echo moo > par/moo
	$(tar) -rf $(@) par/moo
	rm -rf par

.error = GNU make is required

# vim:ts=4 sts=4 sw=4 noet
