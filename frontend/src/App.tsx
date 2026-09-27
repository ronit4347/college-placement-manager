import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './layouts/AppLayout'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import RoleAreaPage from './pages/RoleAreaPage'
import StudentDashboardPage from './pages/StudentDashboardPage'
import UnauthorizedPage from './pages/UnauthorizedPage'
import WorkspacePage from './pages/WorkspacePage'
import CompaniesPage from './pages/CompaniesPage'
import CompanyDetailsPage from './pages/CompanyDetailsPage'
import CompanyFormPage from './pages/CompanyFormPage'
import JobDrivesPage from './pages/JobDrivesPage'
import JobDriveFormPage from './pages/JobDriveFormPage'
import JobDriveDetailsPage from './pages/JobDriveDetailsPage'
import JobDriveApplicantsPage from './pages/JobDriveApplicantsPage'
import ApplicationsPage from './pages/ApplicationsPage'
import ApplicationDetailsPage from './pages/ApplicationDetailsPage'
import InterviewsPage from './pages/InterviewsPage'
import OffersPage from './pages/OffersPage'
import StudentsPage from './pages/StudentsPage'
import InterviewersPage from './pages/InterviewersPage'

const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'))

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/workspace" element={<WorkspacePage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['STUDENT', 'ADMIN', 'RECRUITER']} />}>
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/applications/:applicationId" element={<ApplicationDetailsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['STUDENT', 'ADMIN', 'INTERVIEWER']} />}>
          <Route path="/interviews" element={<InterviewsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['STUDENT', 'ADMIN', 'RECRUITER']} />}>
          <Route path="/offers" element={<OffersPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['STUDENT']} />}>
          <Route path="/student" element={<StudentDashboardPage />} />
          <Route path="/student/offers" element={<OffersPage />} />
          <Route path="/student/job-drives" element={<JobDrivesPage audience="STUDENT" />} />
          <Route path="/student/job-drives/:driveId" element={<JobDriveDetailsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['ADMIN']} />}>
          <Route path="/admin" element={<Suspense fallback={<p className="p-6 text-sm text-muted">Loading dashboard…</p>}><AdminDashboardPage /></Suspense>} />
          <Route path="/admin/students" element={<StudentsPage />} />
          <Route path="/admin/interviewers" element={<InterviewersPage />} />
          <Route path="/admin/interviews" element={<InterviewsPage />} />
          <Route path="/admin/offers" element={<OffersPage />} />
          <Route path="/admin/companies" element={<CompaniesPage />} />
          <Route path="/admin/companies/new" element={<CompanyFormPage />} />
          <Route path="/admin/companies/:companyId" element={<CompanyDetailsPage />} />
          <Route path="/admin/companies/:companyId/edit" element={<CompanyFormPage />} />
          <Route path="/admin/job-drives" element={<JobDrivesPage audience="ADMIN" />} />
          <Route path="/admin/job-drives/new" element={<JobDriveFormPage />} />
          <Route path="/admin/job-drives/:driveId" element={<JobDriveDetailsPage />} />
          <Route path="/admin/job-drives/:driveId/edit" element={<JobDriveFormPage />} />
          <Route path="/admin/job-drives/:driveId/applicants" element={<JobDriveApplicantsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['RECRUITER']} />}>
          <Route path="/recruiter" element={<RoleAreaPage role="RECRUITER" />} />
          <Route path="/recruiter/offers" element={<OffersPage />} />
          <Route path="/recruiter/job-drives" element={<JobDrivesPage audience="RECRUITER" />} />
          <Route path="/recruiter/job-drives/:driveId" element={<JobDriveDetailsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['INTERVIEWER']} />}>
          <Route path="/interviewer" element={<RoleAreaPage role="INTERVIEWER" />} />
          <Route path="/interviewer/interviews" element={<InterviewsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['STUDENT']} />}>
          <Route path="/student/interviews" element={<InterviewsPage />} />
        </Route>
        <Route path="*" element={<HomePage />} />
      </Route>
    </Routes>
  )
}
