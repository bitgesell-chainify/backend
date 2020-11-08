const { KJUR } = require('jsrsasign');

let response;

exports.generateInstantToken = async (event, context) => {
    try {
        const body = JSON.parse(event['body'])
        const { sdkKey, sdkSecret, topic, password } = body;

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

        // const ret = await axios(url);
        response = {
            'statusCode': 200,
            'body': JSON.stringify({signature})
        }
    } catch (err) {
        console.log(err);
        return err;
    }

    return response
};