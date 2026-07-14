from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 允許跨域請求 (供 Flutter App 呼叫)
    CORS(app)

    # 健康檢查 API
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "MedPulse Flask Core API",
            "version": "1.0.0"
        }), 200

    return app

app = create_app()

if __name__ == "__main__":
    # 將 port 從 5000 改為 5001
    app.run(host="0.0.0.0", port=5001, debug=True)