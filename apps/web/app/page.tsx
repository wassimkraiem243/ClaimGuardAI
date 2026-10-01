import { PreSubmissionFlow } from '../components/PreSubmissionFlow';

export const metadata = {
  title: 'Pre-submission validation | ClaimGuard AI',
  description: 'Upload a claim, run payer rules, and review results before submission.',
};

export default function HomePage() {
  return <PreSubmissionFlow />;
}
