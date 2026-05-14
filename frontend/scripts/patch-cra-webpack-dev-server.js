const fs = require('fs');
const path = require('path');

// Applies the CRA 5 middleware compatibility patch needed by webpack-dev-server 5.
const configPath = path.join(
  __dirname,
  '..',
  'node_modules',
  'react-scripts',
  'config',
  'webpackDevServer.config.js'
);

const oldMiddlewareHooks = `    // \`proxy\` is run between \`before\` and \`after\` \`webpack-dev-server\` hooks
    proxy,
    onBeforeSetupMiddleware(devServer) {
      // Keep \`evalSourceMapMiddleware\`
      // middlewares before \`redirectServedPath\` otherwise will not have any effect
      // This lets us fetch source contents from webpack for the error overlay
      devServer.app.use(evalSourceMapMiddleware(devServer));

      if (fs.existsSync(paths.proxySetup)) {
        // This registers user provided middleware for proxy reasons
        require(paths.proxySetup)(devServer.app);
      }
    },
    onAfterSetupMiddleware(devServer) {
      // Redirect to \`PUBLIC_URL\` or \`homepage\` from \`package.json\` if url not match
      devServer.app.use(redirectServedPath(paths.publicUrlOrPath));

      // This service worker file is effectively a 'no-op' that will reset any
      // previous service worker registered for the same host:port combination.
      // We do this in development to avoid hitting the production cache if
      // it used the same host and port.
      // https://github.com/facebook/create-react-app/issues/2272#issuecomment-302832432
      devServer.app.use(noopServiceWorkerMiddleware(paths.publicUrlOrPath));
    },`;

const wdsFiveCompatibleHook = `    // \`proxy\` is run between setup middlewares in \`webpack-dev-server\`.
    proxy,
    setupMiddlewares(middlewares, devServer) {
      if (!devServer) {
        throw new Error('webpack-dev-server is not defined');
      }

      // Keep \`evalSourceMapMiddleware\`
      // middlewares before \`redirectServedPath\` otherwise will not have any effect
      // This lets us fetch source contents from webpack for the error overlay
      devServer.app.use(evalSourceMapMiddleware(devServer));

      if (fs.existsSync(paths.proxySetup)) {
        // This registers user provided middleware for proxy reasons
        require(paths.proxySetup)(devServer.app);
      }

      // Redirect to \`PUBLIC_URL\` or \`homepage\` from \`package.json\` if url not match
      devServer.app.use(redirectServedPath(paths.publicUrlOrPath));

      // This service worker file is effectively a 'no-op' that will reset any
      // previous service worker registered for the same host:port combination.
      // We do this in development to avoid hitting the production cache if
      // it used the same host and port.
      // https://github.com/facebook/create-react-app/issues/2272#issuecomment-302832432
      devServer.app.use(noopServiceWorkerMiddleware(paths.publicUrlOrPath));

      return middlewares;
    },`;

const oldHttpsOption = '    https: getHttpsConfig(),';
const wdsFiveServerOption = `    server: (() => {
      const httpsConfig = getHttpsConfig();
      if (!httpsConfig) {
        return 'http';
      }
      return {
        type: 'https',
        options: httpsConfig === true ? {} : httpsConfig,
      };
    })(),`;

if (!fs.existsSync(configPath)) {
  console.warn('[patch-cra-webpack-dev-server] react-scripts config not found');
  process.exit(0);
}

const source = fs.readFileSync(configPath, 'utf8');
let patchedSource = source;
const appliedPatches = [];

if (patchedSource.includes(oldMiddlewareHooks)) {
  patchedSource = patchedSource.replace(oldMiddlewareHooks, wdsFiveCompatibleHook);
  appliedPatches.push('middleware hooks');
} else if (!patchedSource.includes('setupMiddlewares(middlewares, devServer)')) {
  throw new Error(
    '[patch-cra-webpack-dev-server] react-scripts dev server config shape changed'
  );
}

if (patchedSource.includes(oldHttpsOption)) {
  patchedSource = patchedSource.replace(oldHttpsOption, wdsFiveServerOption);
  appliedPatches.push('server option');
} else if (!patchedSource.includes('server: (() => {')) {
  throw new Error(
    '[patch-cra-webpack-dev-server] react-scripts https config shape changed'
  );
}

if (patchedSource === source) {
  process.exit(0);
}

fs.writeFileSync(configPath, patchedSource);

console.log(
  `[patch-cra-webpack-dev-server] patched react-scripts dev server config: ${appliedPatches.join(', ')}`
);
