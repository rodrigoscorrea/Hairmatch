const fs = require('fs');

// Adds to app.json what depends on the environment. The Firebase file holds the project keys, so it stays out of git:
// the EAS build gets it as a file variable (GOOGLE_SERVICES_JSON) and a local build reads ./google-services.json.
// Without either the key is left out and the build still works: the app just gets no push token (NOTIF-16).
const googleServicesFile = process.env.GOOGLE_SERVICES_JSON ?? (fs.existsSync('./google-services.json') ? './google-services.json' : undefined);

module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    ...(googleServicesFile ? { googleServicesFile } : {}),
  },
});
