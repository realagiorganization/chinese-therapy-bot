module.exports = {
  root: true,
  extends: ["universe/native"],
  parserOptions: {
    tsconfigRootDir: __dirname,
    project: "./tsconfig.json"
  },
  ignorePatterns: ["node_modules/", "dist/", "build/"]
};
