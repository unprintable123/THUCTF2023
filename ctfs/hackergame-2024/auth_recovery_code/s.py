from sage.all import *
import requests
import base64
import hashlib
import hmac
import random
import struct
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
import random

x = GF(2)["x"].gen()
gf2e = GF(2 ** 128, name="y", modulus=x ** 128 + x ** 7 + x ** 2 + x + 1)

# https://github.com/jvdsn/crypto-attacks/blob/master/attacks/gcm/forbidden_attack.py

# Converts an integer to a gf2e element, little endian.
def _to_gf2e(n):
    return gf2e([(n >> i) & 1 for i in range(127, -1, -1)])


# Converts a gf2e element to an integer, little endian.
def _from_gf2e(p):
    # n = p.integer_representation()
    # ans = 0
    # for i in range(128):
    #     ans <<= 1
    #     ans |= ((n >> i) & 1)

    # return ans
    return p.to_integer(True)


# Calculates the GHASH polynomial.
def _ghash(h, a, c):
    la = len(a)
    lc = len(c)
    p = gf2e(0)
    for i in range(la // 16):
        p += _to_gf2e(int.from_bytes(a[16 * i:16 * (i + 1)], byteorder="big"))
        p *= h

    if la % 16 != 0:
        p += _to_gf2e(int.from_bytes(a[-(la % 16):] + bytes(16 - la % 16), byteorder="big"))
        p *= h

    for i in range(lc // 16):
        p += _to_gf2e(int.from_bytes(c[16 * i:16 * (i + 1)], byteorder="big"))
        p *= h

    if lc % 16 != 0:
        p += _to_gf2e(int.from_bytes(c[-(lc % 16):] + bytes(16 - lc % 16), byteorder="big"))
        p *= h

    p += _to_gf2e(((8 * la) << 64) | (8 * lc))
    p *= h
    return p


def recover_possible_auth_keys(a1, c1, t1, a2, c2, t2):
    """
    Recovers possible authentication keys from two messages encrypted with the same authentication key.
    More information: Joux A., "Authentication Failures in NIST version of GCM"
    :param a1: the associated data of the first message (bytes)
    :param c1: the ciphertext of the first message (bytes)
    :param t1: the authentication tag of the first message (bytes)
    :param a2: the associated data of the second message (bytes)
    :param c2: the ciphertext of the second message (bytes)
    :param t2: the authentication tag of the second message (bytes)
    :return: a generator generating possible authentication keys (gf2e element)
    """
    h = gf2e["h"].gen()
    p1 = _ghash(h, a1, c1) + _to_gf2e(int.from_bytes(t1, byteorder="big"))
    p2 = _ghash(h, a2, c2) + _to_gf2e(int.from_bytes(t2, byteorder="big"))
    for h, _ in (p1 + p2).roots():
        yield h


def forge_tag(h, a, c, t, target_a, target_c):
    """
    Forges an authentication tag for a target message given a message with a known tag.
    This method is best used with the authentication keys generated by the recover_possible_auth_keys method.
    More information: Joux A., "Authentication Failures in NIST version of GCM"
    :param h: the authentication key to use (gf2e element)
    :param a: the associated data of the message with the known tag (bytes)
    :param c: the ciphertext of the message with the known tag (bytes)
    :param t: the known authentication tag (bytes)
    :param target_a: the target associated data (bytes)
    :param target_c: the target ciphertext (bytes)
    :return: the forged authentication tag (bytes)
    """
    ghash = _from_gf2e(_ghash(h, a, c))
    target_ghash = _from_gf2e(_ghash(h, target_a, target_c))
    return (ghash ^ int.from_bytes(t, byteorder="big") ^ target_ghash).to_bytes(16, byteorder="big")






def register(username, password):
    return requests.post(url + "/register", json={"username": base64.b64encode(username.encode()).decode(), "password": base64.b64encode(password.encode()).decode()})

def login(username, password):
    return requests.post(url + "/login", json={"username": base64.b64encode(username.encode()).decode(), "password": base64.b64encode(password.encode()).decode()})

def recover(recovery_code: bytes, super_mode: bool, new_password: str):
    return requests.post(url + "/recover", json={"recovery_code": base64.b64encode(recovery_code).decode(), "super_mode": super_mode, "new_password": new_password})

def get_nonce(username, password):
    hmac_hash = hmac.new(username.encode(), password.encode(), hashlib.sha256).digest()

    return hmac_hash[:12]

def decompose_recovery_code(recovery_code: bytes):
    len1 = int.from_bytes(recovery_code[:8], "little")
    ct = recovery_code[8:8+len1]
    len2 = int.from_bytes(recovery_code[8+len1:16+len1], "little")
    nonce = recovery_code[16+len1:16+len1+len2]
    len3 = int.from_bytes(recovery_code[16+len1+len2:24+len1+len2], "little")
    ad = recovery_code[24+len1+len2:]
    return ct, nonce, ad

def pack_recovery_code(ct: bytes, nonce: bytes, ad: bytes):
    return len(ct).to_bytes(8, "little") + ct + len(nonce).to_bytes(8, "little") + nonce + len(ad).to_bytes(8, "little") + ad

SERCET_KEY = bytes.fromhex("5d, 9e, 06, 07, 0e, 5f, cd, d5, 8f, c9, f6, c5, 07, 78, d0, ed, 8a, 84, b4, d7, fa, 53, 95, 17, ec, 05, e8, ed, 64, ed, 1f, f8".replace(",", ""))

def gcm_encrypt(data: bytes, nonce: bytes, ad: bytes):
    cipher = AES.new(SERCET_KEY, AES.MODE_GCM, nonce=nonce)
    cipher.update(ad)
    ct, tag = cipher.encrypt_and_digest(data)
    return ct, tag

def get_ct_tag(username, password):
    recovery_code = register(username, password).json()
    ct, nonce, ad = decompose_recovery_code(base64.b64decode(recovery_code))
    assert nonce == get_nonce(username, password), (nonce, get_nonce(username, password))
    real_ct = ct[:len(ct) - 16]
    real_tag = ct[-16:]
    # print(real_ct, real_tag)
    return real_ct, real_tag

def gen_superuser():
    user = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))
    print(user)

    ct1, tag1 = get_ct_tag(user, "333")
    ct2, tag2 = get_ct_tag(f"{user}\x00", "333")
    ct3, tag3 = get_ct_tag(f"{user}\x00\x00", "333")

    l1 = list(recover_possible_auth_keys(b'admin=false', ct1, tag1, b'admin=false', ct2, tag2))
    l2 = list(recover_possible_auth_keys(b'admin=false', ct1, tag1, b'admin=false', ct3, tag3))

    for h in l1:
        if h in l2:
            break
    assert h in l1 and h in l2
    # print(h)

    ftag = forge_tag(h, b'admin=false', ct1, tag1, b'admin=true', ct1)
    fake_recovery_code = pack_recovery_code(ct1 + ftag, get_nonce(user, "333"), b'admin=true')

    print(recover(fake_recovery_code, False, "333").json())
    return login(user, "333").json()[0]

def generate_super_key(username, pin):
    hasher = hashlib.sha256()
    hasher.update(username.encode('utf-8'))
    hasher.update(pin.encode('utf-8'))
    return hasher.digest()

def get_default_tag(key, nonce):
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(b'admin=true')
    ct, tag = cipher.encrypt_and_digest(b'\x00'*LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(b'admin=true')
    ct2, tag2 = cipher.encrypt_and_digest(ct)
    return _to_gf2e(int.from_bytes(tag2, 'big'))

def decode_to_bytes(s):
    return _from_gf2e(s).to_bytes(16, 'big')

def get_h(key):
    cipher = AES.new(key, AES.MODE_ECB)
    return _to_gf2e(int.from_bytes(cipher.encrypt(b'\x00'*16), 'big'))

def forge_sign(key_pairs):
    poly = 0
    R = PolynomialRing(gf2e, 'h')
    var_h = R.gen()

    inter_poly = R.lagrange_polynomial([(kh, kt/(kh**2)) for _, kt, kh in key_pairs]) * var_h**2

    sl = inter_poly.list()[2:]

    enc_bytes = [decode_to_bytes(s) for s in sl]

    enc_bytes.reverse()

    pt = b''.join(enc_bytes)
    return b'\x00'* (LEN - len(pt)) + pt

def check_keys(key_pairs):
    c = forge_sign(key_pairs)

    res = recover(pack_recovery_code(c + b'\x00'*16, nonce, b'admin=true'), True, "333")

    return res.status_code == 404

def try_solve(superkeys):
    nonce = get_nonce(admin_name, "333")
    hs = [get_h(key) for key in superkeys]
    default_tags = [get_default_tag(key, nonce) for key in superkeys]


    assert len(superkeys) == len(default_tags) == len(hs)

    superkey_pairs = list(zip(superkeys, default_tags, hs))

    if check_keys(superkey_pairs) == False:
        print("Failed")
        return
    print("Success")
    
    left = 0
    right = len(superkeys)
    while right - left > 1:
        mid = (left + right) // 2
        if mid == left:
            mid += 1
        if check_keys(superkey_pairs[left:mid]):
            right = mid
        else:
            left = mid
    print("Find:", superkeys[left:right], left, right)
    real_key = superkeys[left]
    
    cipher = AES.new(real_key, AES.MODE_GCM, nonce=nonce)
    cipher.update(b'admin=true')
    ct, tag = cipher.encrypt_and_digest(admin_name.encode())
    print(recover(pack_recovery_code(ct + tag, nonce, b'admin=true'), True, "333").json())
    print(login(admin_name, "333").json())

# url = "http://172.19.144.1:21111"
url = "https://chal00-4bgs5y33.hack-challenge.lug.ustc.edu.cn:8443/"
LEN = 16 * 2024


import sys, json

if len(sys.argv) > 1:
    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    print(start_idx, end_idx)
    with open("superkeys.json", "r") as f:
        data = json.load(f)
        admin_name = data["admin_name"]
        superkeys = [base64.b64decode(k) for k in data["superkeys"]]
    nonce = get_nonce(admin_name, "333")
    try_solve(superkeys[start_idx:end_idx])
else:
    jwt_token = gen_superuser()

    headers = {
        "Authorization": f"Bearer {jwt_token}"
    }

    users = requests.get(f"{url}/users", headers=headers).json()[1]

    admin_name = None
    for user in users:
        if base64.b64decode(user["username"]).decode().startswith("ADMIN"):
            admin_name = base64.b64decode(user["username"]).decode()
            break

    assert admin_name is not None

    print(admin_name)
    
    superkeys = []
    for pin in range(10**6):
        pin = str(pin).zfill(6)
        if "9" in pin or "8" in pin: # or "7" in pin or "6" in pin:
            continue
        superkeys.append(generate_super_key(admin_name, pin))
    random.shuffle(superkeys)

    print(len(superkeys))

    with open("superkeys.json", "w") as f:
        json.dump({
            "admin_name": admin_name,
            "superkeys": [base64.b64encode(k).decode() for k in superkeys]
        }, f)
    
    import pwn

    poll = []
    for i in range(16):
        p = pwn.process(["sage", "s.py", str(i*2000), str((i+1)*2000)], stdout=sys.stdout, stderr=sys.stderr)
        poll.append(p)
    
    for p in poll:
        p.wait_for_close()






