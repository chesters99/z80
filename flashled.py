import time
from uctypes import INT8
from micropython import const

vali=1 ;
valx=0x01; 
valb=0b000001; 
valz=INT8; 
valc = const(1);

limit =100000

start = time.ticks_ms()
for y in range(limit):
    x = 27 & vali
end = time.ticks_ms()
print("vali", time.ticks_diff(end, start))

#start = time.time()
#for y in range(limit):
#    x = 27 & valx
#print("valx", time.time() - start)

#start = time.time()
#for y in range(limit):
#    x = 27 & valb
#print("valb", time.time() - start)

#start = time.time()
#for y in range(limit):
#    x = y & valz
#print("valz", time.time() - start)

#start = time.time()
#for y in range(limit):
#    x = 27 & valc
#print("valc", time.time() - start)
