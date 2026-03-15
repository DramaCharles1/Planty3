import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import vitest from 'eslint-plugin-vitest';
import globals from 'globals';
import prettier from 'eslint-config-prettier';

export default [
  // Base recommended rules
  js.configs.recommended,

  // React configuration
  {
    files: ['**/*.{js,jsx}'],
    plugins: {
      react,
      'react-hooks': reactHooks,
    },
    languageOptions: {
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      // Allow React imports even though not strictly needed with new JSX transform
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',
      // Disable prop-types requirement (not using TypeScript or PropTypes in this project)
      'react/prop-types': 'off',
    },
  },

  // Vitest configuration for test files
  {
    files: ['src/test/**/*.{js,jsx}'],
    plugins: {
      vitest,
    },
    languageOptions: {
      globals: {
        ...globals.node,
        ...vitest.environments.env.globals,
      },
    },
    rules: {
      ...vitest.configs.recommended.rules,
    },
  },

  // Prettier config (must be last to disable conflicting rules)
  prettier,
];
