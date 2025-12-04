const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "..");

const config = getDefaultConfig(projectRoot);

const alias = {
  "@theme": path.resolve(projectRoot, "src/theme"),
  "@components": path.resolve(projectRoot, "src/components"),
  "@screens": path.resolve(projectRoot, "src/screens"),
  "@hooks": path.resolve(projectRoot, "src/hooks"),
  "@context": path.resolve(projectRoot, "src/context"),
  "@services": path.resolve(projectRoot, "src/services"),
  "@types": path.resolve(projectRoot, "src/types"),
  shared: path.join(workspaceRoot, "shared")
};

config.watchFolders = [path.join(workspaceRoot, "shared")];

config.resolver.disableHierarchicalLookup = false;
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, "node_modules"),
  path.resolve(workspaceRoot, "node_modules")
];
config.resolver.alias = alias;

module.exports = config;
