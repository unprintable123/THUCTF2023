
from Crypto.Util.number import bytes_to_long
import random
rng = random.SystemRandom()

flag = b'FAKE{THIS_IS_FAKE_FLAG}'
secret = bytes_to_long(flag + rng.randbytes(1024//8-1-len(flag)))


a, b = [0x1c456bfc3fabba99a737d7fd127eaa9661f7f02e9eb2d461d7398474a93a9b87,0x8b429f4b9d14ed4307ee460e9f8764a1f276c7e5ce3581d8acd4604c2f0ee7ca]
X,Y,Z = (92512155407887452984968972936950900353410451673762367867085553821839087925110135228608997461366439417183638759117086992178461481890351767070817400228450804002809798219652013051455151430702918340448295871270728679921874136061004110590203462981486702691470087300050508138714919065755980123700315785502323688135 ,40665795291239108277438242660729881407764141249763854498178188650200250986699 , 1)

p = 0xd9d35163a870dc6dfb7f43911ff81c964dc8e1dd2481fdf6f0e653354b59c5e5
ec = EllipticCurve(Zmod(p**4),[a,b])
P = ec.point((X,Y,Z))

ec0 = EllipticCurve(Zmod(p),[a,b])
n = 0xd9d35163a870dc6dfb7f43911ff81c964dc8e1dd2481fdf6f0e653354b59c5e5

assert (n*p**3+241421)*P == 241421*P

# print((secret*P).xy())

target = ec.point((62273117814745802387117000953578316639782644586418639656941009579492165136792362926314161168383693280669749433205290570927417529976956408493670334719077164685977962663185902752153873035889882369556401683904738521640964604463617065151463577392262554355796294028620255379567953234291193792351243682705387292519, 518657271161893478053627976020790808461429425062738029168194264539097572374157292255844047793806213041891824369181319495179810050875252985460348040004008666418463984493701257711442508837320224308307678689718667843629104002610613765672396802249706628141469710796919824573605503050908305685208558759526126341))

# 60127352936792332954241644848990217302370773273213540688804531951981291541112 mod p

m0 = 60127352936792332954241644848990217302370773273213540688804531951981291541112

# (target - m0*P)*(p**2)



P3 = (p**3+1)*P

diff = ZZ(P3.x()-P.x())
assert diff % (p**3) == 0
diff //= p**3

T1 = (P+(p**2+1)*target-(p**2-1)*m0*P)-target-m0*P # P + m1*p**3*P


m1 = (ZZ(T1.x()-P.x()) // (p**3))*inverse_mod(diff,p)%p

# (target - m0*P - m1*p*P)*p

T2 = P+(p+1)*target-target-(p-1)*(m0+m1*p)*P-(m0+m1*p)*P

m2 = (ZZ(T2.x()-P.x()) // (p**3))*inverse_mod(diff,p)%p

m02 = m0 + m1*p + m2*p**2

# (target - m02*P)

T3 = P+target-m02*P

assert ZZ(T3.x()-P.x()) % (p**3)==0

m3 = (ZZ(T3.x()-P.x()) // (p**3))*inverse_mod(diff,p)%p

m = m02 + m3*p**3

print(bytes.fromhex(hex(m)[2:]))
