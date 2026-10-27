# Supplement, rather than modify, the historical radix-tree Makefile.
CONSUMER_OFILES := xarray.o radix-tree.o idr.o linux.o test.o find_bit.o bitmap.o slab.o

consumer-probe: consumer_probe.o $(CONSUMER_OFILES)
	$(CC) $(LDFLAGS) -o $@ $^ $(LDLIBS)
