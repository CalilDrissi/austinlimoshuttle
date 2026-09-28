import type { Preview } from "@storybook/react";

// Load the same CSS stack as the app
import "../src/styles/vendors/normalize.css";
import "../src/styles/vendors/bootstrap.min.css";
import "../src/styles/vendors/uicons-regular-rounded.css";
import "../src/styles/vendors/animate.css";
import "swiper/css";
import "swiper/css/navigation";
import "swiper/css/pagination";
import "../src/styles/luxride.css";

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
    layout: "fullscreen",
    backgrounds: {
      default: "light",
      values: [
        { name: "light", value: "#ffffff" },
        { name: "dark", value: "#0E0E0E" },
        { name: "grey", value: "#f5f5f5" },
      ],
    },
  },
};

export default preview;
