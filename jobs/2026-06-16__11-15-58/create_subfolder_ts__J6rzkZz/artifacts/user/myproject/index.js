"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const unify_1 = require("@apideck/unify");
const fs = __importStar(require("fs"));
async function main() {
    const appId = process.env.APIDECK_APP_ID;
    const apiKey = process.env.APIDECK_API_KEY;
    const consumerId = process.env.APIDECK_CONSUMER_ID;
    const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
    const runId = process.env.ZEALT_RUN_ID;
    const apideck = new unify_1.Apideck({
        apiKey,
        appId,
        consumerId,
    });
    console.log('Fetching drives...');
    let targetDriveId;
    const drivesResponse = await apideck.fileStorage.drives.list({
        serviceId: 'onedrive',
    });
    // The drives listing endpoint returns a paginated iterable
    for await (const page of drivesResponse) {
        const drives = page.getDrivesResponse?.data || [];
        for (const drive of drives) {
            if (drive.name === driveName) {
                targetDriveId = drive.id;
                break;
            }
        }
        if (targetDriveId)
            break;
    }
    if (!targetDriveId) {
        throw new Error(`Drive with name ${driveName} not found`);
    }
    console.log(`Found drive: ${targetDriveId}`);
    const parentFolderName = `apideck-parent-${runId}`;
    const childFolderName = `apideck-child-${runId}`;
    console.log(`Creating parent folder: ${parentFolderName}`);
    const parentResponse = await apideck.fileStorage.folders.create({
        serviceId: 'onedrive',
        createFolderRequest: {
            name: parentFolderName,
            parentFolderId: 'root',
            driveId: targetDriveId,
        },
    });
    const parentFolderId = parentResponse.createFolderResponse?.data.id;
    if (!parentFolderId) {
        throw new Error('Failed to create parent folder: no ID returned');
    }
    console.log(`Parent folder created: ${parentFolderId}`);
    console.log(`Creating child folder: ${childFolderName}`);
    const childResponse = await apideck.fileStorage.folders.create({
        serviceId: 'onedrive',
        createFolderRequest: {
            name: childFolderName,
            parentFolderId: parentFolderId,
            driveId: targetDriveId,
        },
    });
    const childFolderId = childResponse.createFolderResponse?.data.id;
    if (!childFolderId) {
        throw new Error('Failed to create child folder: no ID returned');
    }
    console.log(`Child folder created: ${childFolderId}`);
    const logData = {
        drive_id: targetDriveId,
        parent_folder_id: parentFolderId,
        parent_folder_name: parentFolderName,
        child_folder_id: childFolderId,
        child_folder_name: childFolderName,
    };
    fs.writeFileSync('/home/user/myproject/output.log', JSON.stringify(logData, null, 2));
    console.log('Log file written successfully.');
}
main().catch((err) => {
    console.error(err);
    process.exit(1);
});
