/**
 * Sidebar state management for mobile menu
 */

let isOpen = $state(false);

export const sidebar = {
  get isOpen() {
    return isOpen;
  },

  open() {
    isOpen = true;
  },

  close() {
    isOpen = false;
  },

  toggle() {
    isOpen = !isOpen;
  },
};
