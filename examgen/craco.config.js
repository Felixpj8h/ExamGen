const tailwindPostcss = require('@tailwindcss/postcss');

function replaceTailwindPostcssPlugin(plugins) {
  if (!Array.isArray(plugins)) {
    return plugins;
  }
  return plugins.map((plugin) => (plugin === 'tailwindcss' ? tailwindPostcss : plugin));
}

function patchPostcssLoaders(rule) {
  if (!rule || typeof rule !== 'object') {
    return;
  }

  const rules = Array.isArray(rule.oneOf) ? rule.oneOf : rule.rules;
  if (Array.isArray(rules)) {
    rules.forEach(patchPostcssLoaders);
  }

  const use = Array.isArray(rule.use) ? rule.use : [];
  use.forEach((loaderEntry) => {
    if (!loaderEntry || typeof loaderEntry !== 'object') {
      return;
    }
    if (!String(loaderEntry.loader || '').includes('postcss-loader')) {
      return;
    }

    const postcssOptions = loaderEntry.options?.postcssOptions;
    if (!postcssOptions || typeof postcssOptions !== 'object') {
      return;
    }
    if (Array.isArray(postcssOptions.plugins)) {
      postcssOptions.plugins = replaceTailwindPostcssPlugin(postcssOptions.plugins);
    } else if (typeof postcssOptions.plugins === 'function') {
      const originalPlugins = postcssOptions.plugins;
      postcssOptions.plugins = (...args) => replaceTailwindPostcssPlugin(originalPlugins(...args));
    }
  });
}

function patchSourceMapLoaders(rule) {
  if (!rule || typeof rule !== 'object') {
    return;
  }

  const rules = Array.isArray(rule.oneOf) ? rule.oneOf : rule.rules;
  if (Array.isArray(rules)) {
    rules.forEach(patchSourceMapLoaders);
  }

  if (String(rule.loader || '').includes('source-map-loader')) {
    rule.exclude = [
      ...(Array.isArray(rule.exclude) ? rule.exclude : rule.exclude ? [rule.exclude] : []),
      /node_modules[\\/]d3-/,
      /node_modules[\\/]internmap/,
    ];
  }

  const use = Array.isArray(rule.use) ? rule.use : [];
  use.forEach((loaderEntry) => {
    if (!loaderEntry || typeof loaderEntry !== 'object') {
      return;
    }
    if (!String(loaderEntry.loader || '').includes('source-map-loader')) {
      return;
    }

    loaderEntry.exclude = [
      ...(Array.isArray(loaderEntry.exclude) ? loaderEntry.exclude : loaderEntry.exclude ? [loaderEntry.exclude] : []),
      /node_modules[\\/]d3-/,
      /node_modules[\\/]internmap/,
    ];
  });
}

module.exports = {
  jest: {
    configure: (jestConfig) => {
      jestConfig.transformIgnorePatterns = [
        '[\\\\/]node_modules[\\\\/](?!(d3-[^\\\\/]+|internmap)[\\\\/]).+\\.(js|jsx|mjs|cjs|ts|tsx)$',
        '^.+\\.module\\.(css|sass|scss)$',
      ];
      return jestConfig;
    },
  },
  webpack: {
    configure: (webpackConfig) => {
      webpackConfig.module.rules.forEach(patchPostcssLoaders);
      webpackConfig.module.rules.forEach(patchSourceMapLoaders);
      return webpackConfig;
    },
  },
};
