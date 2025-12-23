import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
  // Redirect root to Discover page
  throw redirect(302, '/discover');
};
