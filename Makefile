LIB_LOCATION=/usr/lib/wb-homa-ism-radio
.PHONY: all clean

all:
clean :

install: all
	install -m 0644 *.py  $(DESTDIR)/$(LIB_LOCATION)/
	install -m 0755 wb-homa-rcd.py  $(DESTDIR)/$(LIB_LOCATION)/
	install -m 0755 wb-homa-ism-radio  $(DESTDIR)/etc/init.d/

	-rm $(DESTDIR)/usr/bin/wb-homa-rcd
	ln -s $(LIB_LOCATION)/wb-homa-rcd.py $(DESTDIR)/usr/bin/wb-homa-rcd


