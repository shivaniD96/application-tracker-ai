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

interface JobDetailsModalProps {
  open: boolean;
  onClose: () => void;
  job: any | null;
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
                  {job.requirements.map((req: string, idx: number) => (
                    <ListItem key={idx} disablePadding>
                      <ListItemText primary={req} />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
            {Array.isArray(job.suggestions) && job.suggestions.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>Suggestions:</Typography>
                <List dense>
                  {job.suggestions.map((s: any, idx: number) => (
                    <ListItem key={idx} disablePadding>
                      <ListItemText primary={s.suggestion} />
                    </ListItem>
                  ))}
                </List>
              </>
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