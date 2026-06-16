"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const unify_1 = require("@apideck/unify");
const apideck = new unify_1.Apideck({
    apiKey: 'fake',
    appId: 'fake',
    consumerId: 'fake',
});
async function test() {
    const drivesResponse = await apideck.fileStorage.drives.list({
        serviceId: 'onedrive',
    });
    console.log(drivesResponse);
}
