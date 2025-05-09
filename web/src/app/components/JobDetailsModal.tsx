import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

interface Suggestion {
  category: string;
  suggestion: string;
  action_items: string[];
}

interface Job {
  id?: number;
  title: string;
  company: string;
  location: string;
  platform: string;
  description: string;
  requirements: string[];
  suggestions: Suggestion[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

interface JobDetailsModalProps {
  open: boolean;
  onClose: () => void;
  job: Job | null;
}

export default function JobDetailsModal({ open, onClose, job }: JobDetailsModalProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth scroll="paper">
      {job ? (
        <>
          <DialogTitle>{job.title}</DialogTitle>
          <DialogContent dividers>
            <Typography variant="subtitle1" color="text.secondary" gutterBottom>{job.company}</Typography>
            <Typography variant="body2" gutterBottom><strong>Location:</strong> {job.location}</Typography>
            <Typography variant="body2" gutterBottom><strong>Platform:</strong> {job.platform}</Typography>
            {job.description && job.description !== 'Click "Details" to view full description' && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>Description:</Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>{job.description}</Typography>
              </>
            )}
            {Array.isArray(job.requirements) && job.requirements.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>Requirements:</Typography>
                <List dense>
                  {job.requirements.map((req, idx) => (
                    <ListItem key={idx} disablePadding>
                      <ListItemText primary={req} />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
            {job && job.suggestions && job.suggestions.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography variant="subtitle1" gutterBottom>Suggestions</Typography>
                <ul>
                  {job.suggestions.map((s: Suggestion, idx: number) => (
                    <li key={idx}>
                      <strong>{s.category}:</strong> {s.suggestion}
                      {s.action_items && s.action_items.length > 0 && (
                        <ul>
                          {s.action_items.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose} color="secondary">Close</Button>
            <Button href={job.url} target="_blank" rel="noopener noreferrer" variant="contained" color="primary">View Original Posting</Button>
          </DialogActions>
        </>
      ) : (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="300px" p={4}>
          <CircularProgress color="primary" />
          <Typography variant="body1" sx={{ mt: 2 }}>Loading job details...</Typography>
        </Box>
      )}
    </Dialog>
  );
} 