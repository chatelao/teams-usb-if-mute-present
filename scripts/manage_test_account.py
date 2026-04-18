import secrets
import string
import os
import sys

def generate_random_string(length):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def main():
    target_file = "test/ACCOUNT.md"

    if os.path.exists(target_file):
        print(f"Credentials already exist in {target_file}. Skipping generation.")
        return

    print(f"Credentials missing. Generating new test account...")

    username = f"testuser_{generate_random_string(6)}"
    password = generate_random_string(16)

    content = f"""# Test Account Credentials

- **Username:** {username}
- **Password:** {password}
"""

    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w") as f:
        f.write(content)

    print(f"Successfully created {target_file} with account: {username}")

if __name__ == "__main__":
    main()
