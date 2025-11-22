const webpack = require('webpack');
const path = require('path');

export default {
  webpack(config, env, helpers, options) {
    if (env.isProd) {
      config.devtool = false;
      config.output = {
        ...config.output,
        path: path.resolve(__dirname, 'build'),
      };
    }
  },
};
