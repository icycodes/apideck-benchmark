"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const unify_1 = require("@apideck/unify");
const apideck = new unify_1.Apideck({ apiKey: 'a', appId: 'a', consumerId: 'a' });
async function check() {
    const drivesResponse = await apideck.fileStorage.drives.list({
        serviceId: 'onedrive',
    });
    console.log(Object.keys(drivesResponse));
}
check().catch(console.error);
