module.exports = function (api) {
  api.cache(true);

  const alias = {
    "@theme": "./src/theme",
    "@components": "./src/components",
    "@screens": "./src/screens",
    "@hooks": "./src/hooks",
    "@context": "./src/context",
    "@services": "./src/services",
    "@types": "./src/types"
  };

  return {
    presets: ["babel-preset-expo"],
    plugins: [
      [
        "module-resolver",
        {
          root: ["./"],
          alias,
          extensions: [".ts", ".tsx", ".js", ".jsx", ".json"]
        }
      ]
    ]
  };
};
