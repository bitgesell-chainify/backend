// import { KJUR } from "jsrsasign";
// https://www.npmjs.com/package/jsrsasign

function generateInstantToken(sdkKey, sdkSecret, topic, password = "") {
  let signature = "";
  // try {
  const iat = Math.round(new Date().getTime() / 1000);
  const exp = iat + 60 * 60 * 2;

  // Header
  const oHeader = { alg: "HS256", typ: "JWT" };
  // Payload
  const oPayload = {
    app_key: sdkKey,
    iat,
    exp,
    tpc: topic,
    pwd: password,
  };
  // Sign JWT
  const sHeader = JSON.stringify(oHeader);
  const sPayload = JSON.stringify(oPayload);
  signature = KJUR.jws.JWS.sign("HS256", sHeader, sPayload, sdkSecret);
  return signature;
}

generateInstantToken(
  your_sdk_key,
  your_sdk_secret,
  session_name,
  session_password
); // call the generateInstantToken function