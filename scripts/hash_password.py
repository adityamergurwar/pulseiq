"""Create a PBKDF2 record for PULSEIQ_USERS_JSON without writing a secret to disk."""
import argparse
import getpass
import hashlib
import json
import secrets

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--username",required=True)
    p.add_argument("--role",choices=["ADMIN","HR","MANAGER","EXECUTIVE"],required=True)
    p.add_argument("--department-id")
    p.add_argument("--team-id")
    a=p.parse_args()
    password=getpass.getpass("Password: ")
    confirm=getpass.getpass("Confirm password: ")
    if len(password)<14: raise SystemExit("Use at least 14 characters.")
    if password!=confirm: raise SystemExit("Passwords did not match.")
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,600_000).hex()
    row={"role":a.role,"password_salt_hex":salt.hex(),"password_pbkdf2_hex":digest}
    if a.department_id: row["department_id"]=a.department_id
    if a.team_id: row["team_id"]=a.team_id
    print(json.dumps({a.username:row},separators=(",",":")))

if __name__=="__main__": main()
