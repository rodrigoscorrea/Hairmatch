// Adds to app.json what depends on the environment. The Firebase file holds the project keys, so it stays out of git:
// the EAS build gets it as a file variable (GOOGLE_SERVICES_JSON) and a local build reads ./google-services.json.
module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    googleServicesFile: process.env.GOOGLE_SERVICES_JSON ?? './google-services.json',
  },
});
