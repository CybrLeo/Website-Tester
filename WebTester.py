import socket
import sys
import ssl

def parse_uri(uri):
    protocol_string = uri.split("://", 1)
    protocol = protocol_string[0]
    remainder = protocol_string[1]

    if "/" in remainder:
        host_port, path = remainder.split("/", 1)
        path = "/" + path
    else:
        host_port = remainder
        path = "/"

    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 80 if protocol == "http" else 443

    return protocol, host, port, path

def open_connection(host, port, protocol):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    if protocol == "https":
        context = ssl.create_default_context()
        s = context.wrap_socket(s, server_hostname=host)
    return s

def send_request(sock, host, path="/"):
    request = f"GET {path}  HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    sock.sendall(request.encode("utf-8"))
    response = b""
    while True:
        data = sock.recv(4096)
        if not data:
            break
        response += data
    sock.close()
    return response

def parse_response(response):
    header_data, body_data = response.split(b"\r\n\r\n", 1)
    headers = header_data.decode("utf-8")
    body = body_data.decode("utf-8")
    return headers, body

def handle_redirects(uri, max_redirects):
    max_redirects = 10
    protocol, host, port, path = parse_uri(uri)
    sock = open_connection(host, port, protocol)
    response = send_request(sock, host, path)
    headers, body = parse_response(response)

    status_line = headers.split("\r\n", 1)[0]
    status_code = status_line.split(" ")[1]

    if status_code in ("301", "302"):
        location = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("location:"):
                location = line.split(":", 1)[1].strip()
                break
        if location:
            print(f"Redirecting to: {location}")
            return handle_redirects(location, max_redirects - 1)
        else:
            return headers, status_code
    else:
        return headers, status_code

def check_support(host, port):
    context = ssl.create_default_context()
    context.set_alpn_protocols(["h2", "http/1.1"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    ssl_sock = context.wrap_socket(sock, server_hostname=host)
    proto = ssl_sock.selected_alpn_protocol()
    ssl_sock.close()
    return "yes" if proto == "h2" else "no"

def extract_cookies(headers):
    cookies = []
    for line in headers.split("\r\n"):
        if line.lower().startswith("set-cookie:"):
            cookie = line.split(":", 1)[1].strip()
            parts = [p.strip() for p in cookie.split(";)")]
            name = parts[0].split("=", 1)[0]
            domain = None
            expires = None

            for part in parts[1:]:
                if part.lower().startswith("domain="):
                    domain = part.split("=", 1)[1]
                elif part.lower().startswith("expires="):
                    expires = part.split("=", 1)[1]
            cookies.append({"name": name, "domain": domain, "expires": expires})

    return cookies

def main():
    uri = sys.stdin.read().strip()
    protocol, host, port, path = parse_uri(uri)
    print(f"website: {host}")

    h2 = "no"
    if protocol == "https":
        h2 = check_support(host, port)
    print(f"1. Supports HTTP/2: {h2}")

    headers, status_code = handle_redirects(uri, 10)

    cookies = extract_cookies(headers)
    print("2. List of Cookies:")
    for cookie in cookies:
        print(f"   - Cookie Name: {cookie['name']}, Domain: {cookie['domain']}, Expires: {cookie['expires']}")
        if not cookies:
            print("   - None")

    password = "yes" if status_code == "401" else "no"
    print(f"3. Password-protected page: {password}")

if __name__ == "__main__":
    main()
