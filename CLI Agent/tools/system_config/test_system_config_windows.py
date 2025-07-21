from windows import *


def run_tests():
    print("=== Environment Variable Test ===")
    print(check_env_variable("JAVA_HOME"))  # Try another like 'PATH' if needed

    print("\n=== Port Check Test ===")
    print(is_port_open(80))       # Common port, may be in use
    print(is_port_open(54321))    # Random port, likely free

    print("\n=== Windows Service Test ===")
    print(is_service_running("wuauserv"))  # Windows Update (usually running)
    print(is_service_running("fake123"))   # Non-existent

    print("\n=== Set Environment Variable Test ===")
    print(set_env_variable("TEST_VAR", "C:\\TestPath", scope="user"))

    print("\n=== Append to PATH Test ===")
    print(append_to_path("C:\\Program Files\\Java\\bin", scope="user"))


if __name__ == "__main__":
    run_tests()
