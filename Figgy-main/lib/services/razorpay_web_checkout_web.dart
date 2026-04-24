// ignore_for_file: avoid_web_libraries_in_flutter, uri_does_not_exist, deprecated_member_use
import 'dart:js_util' as js_util;
import 'dart:html' as html;

Future<Map<String, dynamic>> openRazorpayWebCheckout(Map<String, dynamic> options) async {
  final jsOptions = js_util.jsify(options);
  final promise = js_util.callMethod(html.window, 'openRazorpayCheckout', [jsOptions]);
  final result = await js_util.promiseToFuture<Object?>(promise);
  final dartResult = js_util.dartify(result);
  return Map<String, dynamic>.from(dartResult as Map);
}
