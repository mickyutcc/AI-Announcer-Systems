import os

from dotenv import load_dotenv

load_dotenv()
k = os.getenv("FAL_KEY")
print(f"FAL_KEY is set: {bool(k)}")
print(f"repr: {repr(k)}")
if k:
    print(f"length: {len(k)}")
    print(f"starts with 'Key ': {k.lower().startswith('key ')}")
    print(f"starts with 'Bearer ': {k.lower().startswith('bearer ')}")
    print(f"masked: {(k[:6] + '...' + k[-4:]) if len(k)>10 else '<short_key>'}")
