from flask import Flask, jsonify
import ipaddress
import os

app = Flask(__name__)


def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


@app.route("/")
def index():
    return jsonify({"message": "IP Info API", "version": "1.0.0"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/ip/<ip_address>")
def ip_info(ip_address):
    if not is_valid_ip(ip_address):
        return jsonify({"error": "Invalid IP address"}), 400

    addr = ipaddress.ip_address(ip_address)
    return jsonify({
        "ip": str(addr),
        "version": "IPv6" if addr.version == 6 else "IPv4",
        "is_private": addr.is_private,
        "is_loopback": addr.is_loopback,
        "is_multicast": addr.is_multicast,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)  # nosec B104 - required for containerized deployment
