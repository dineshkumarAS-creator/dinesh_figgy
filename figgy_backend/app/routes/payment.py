import hmac
import hashlib
from flask import Blueprint, request, jsonify, current_app
import razorpay
from datetime import datetime

# Blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

@payment_bp.route('/create_order', methods=['POST'])
def create_order():
    """POST /api/payment/create_order - Creates a Razorpay order before frontend starts checkout."""
    try:
        data = request.get_json() or {}
        # Get tier selection or price (in INR)
        amount = data.get("amount", 0) # Expected to be in whole INR rupees
        
        if not amount or float(amount) <= 0:
            return jsonify({"status": "error", "message": "Invalid amount for order"}), 400

        # Razorpay takes amount in paise (1 INR = 100 paise)
        amount_paise = int(float(amount) * 100)

        # Initialize Razorpay Client
        key_id = current_app.config.get('RAZORPAY_KEY_ID')
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
        
        if not key_id or not key_secret:
            # NO KEYS CONFIGURED: Return demo keys to allow UI flow to continue
            return jsonify({
                "status": "success",
                "order_id": f"order_demo_{int(datetime.now().timestamp())}",
                "amount": amount_paise,
                "currency": "INR",
                "key_id": "rzp_test_demo_key" # Replace with real key in .env
            }), 200

        client = razorpay.Client(auth=(key_id, key_secret))
        
        # Create Order
        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"receipt_{int(datetime.now().timestamp())}",
            "payment_capture": 1 # Auto Capture
        }
        
        order = client.order.create(data=order_data)
        
        return jsonify({
            "status": "success",
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "key_id": key_id
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error creating order: {str(e)}"}), 500

@payment_bp.route('/verify', methods=['POST'])
def verify_payment():
    """POST /api/payment/verify - Verifies Razorpay payment signature after frontend success."""
    try:
        data = request.get_json() or {}
        
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")
        
        print(f"[DEBUG] verify_payment received: order={razorpay_order_id}, payment={razorpay_payment_id}, signature={razorpay_signature}")

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return jsonify({"status": "error", "message": "Missing payment payload"}), 400

        # DEMO MODE: Auto-verify if the IDs match demo patterns
        is_demo_order = (
            (razorpay_order_id and razorpay_order_id.startswith("order_demo_")) or
            razorpay_order_id == "order_web_demo" or
            razorpay_payment_id == "pay_web_demo" or
            razorpay_payment_id == "pay_demo_web"
        )
        
        if is_demo_order:
            print(f"[DEBUG] Demo order detected. Auto-approving.")
            return jsonify({"status": "success", "message": "Demo Payment verified"}), 200

        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
        if not key_secret:
             return jsonify({"status": "error", "message": "Payment gateway not configured"}), 500

        # Verify signature via HMAC
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(key_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

        if generated_signature == razorpay_signature:
            print(f"[DEBUG] Payment signature verified successfully.")
            return jsonify({"status": "success", "message": "Payment verified successfully"}), 200
        else:
            print(f"[DEBUG] Payment signature mismatch! generated={generated_signature}")
            return jsonify({"status": "error", "message": "Invalid payment signature"}), 400
            
    except Exception as e:
        print(f"[ERROR] verify_payment: {e}")
        return jsonify({"status": "error", "message": f"Server Error verifying payment: {str(e)}"}), 500
