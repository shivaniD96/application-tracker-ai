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
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';

interface Suggestion {
  category: string;
  suggestion: string;
  action_items: string[];
}

interface MatchedSkill {
  skills: string[];
  level: string;
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
  match_percentage?: number;
  matched_skills?: { [key: string]: MatchedSkill };
  missing_skills?: { [key: string]: MatchedSkill };
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
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper">
      {job ? (
        <>
          <DialogTitle>{job.title}</DialogTitle>
          <DialogContent dividers>
            <Typography variant="subtitle1" color="text.secondary" gutterBottom>{job.company}</Typography>
            <Typography variant="body2" gutterBottom><strong>Location:</strong> {job.location}</Typography>
            <Typography variant="body2" gutterBottom><strong>Platform:</strong> {job.platform}</Typography>
            
            {job.match_percentage !== undefined && (
              <>
                <Divider sx={{ my: 2 }} />
                <Paper elevation={0} sx={{ p: 2, bgcolor: 'background.default' }}>
                  <Typography variant="h6" gutterBottom>Match Analysis</Typography>
                  <Typography variant="h4" color="primary" gutterBottom>
                    {job.match_percentage.toFixed(1)}% Match
                  </Typography>
                  
                  {job.matched_skills && Object.keys(job.matched_skills).length > 0 && (
                    <Box mt={2}>
                      <Typography variant="subtitle1" gutterBottom>Matched Skills:</Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {Object.entries(job.matched_skills).map(([category, data]) => (
                          <Box key={category}>
                            <Paper elevation={1} sx={{ p: 1, bgcolor: 'success.light' }}>
                              <Typography variant="subtitle2">{category}</Typography>
                              <List dense>
                                {data.skills.map((skill, idx) => (
                                  <ListItem key={idx} disablePadding>
                                    <ListItemText 
                                      primary={`${skill} (${data.level})`}
                                      primaryTypographyProps={{ variant: 'body2' }}
                                    />
                                  </ListItem>
                                ))}
                              </List>
                            </Paper>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  )}

                  {job.missing_skills && Object.keys(job.missing_skills).length > 0 && (
                    <Box mt={2}>
                      <Typography variant="subtitle1" gutterBottom>Missing Skills:</Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {Object.entries(job.missing_skills).map(([category, data]) => (
                          <Box key={category}>
                            <Paper elevation={1} sx={{ p: 1, bgcolor: 'error.light' }}>
                              <Typography variant="subtitle2">{category}</Typography>
                              <List dense>
                                {data.skills.map((skill, idx) => (
                                  <ListItem key={idx} disablePadding>
                                    <ListItemText 
                                      primary={`${skill} (${data.level})`}
                                      primaryTypographyProps={{ variant: 'body2' }}
                                    />
                                  </ListItem>
                                ))}
                              </List>
                            </Paper>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  )}
                </Paper>
              </>
            )}

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
            
            {job.suggestions && job.suggestions.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" gutterBottom>Suggestions</Typography>
                <List>
                  {job.suggestions.map((s: Suggestion, idx: number) => (
                    <ListItem key={idx} sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                      <Typography variant="subtitle2" color="primary">
                        {s.category}:
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        {s.suggestion}
                      </Typography>
                      {s.action_items && s.action_items.length > 0 && (
                        <List dense sx={{ pl: 2, mt: 0.5 }}>
                          {s.action_items.map((item, i) => (
                            <ListItem key={i} disablePadding>
                              <ListItemText primary={item} />
                            </ListItem>
                          ))}
                        </List>
                      )}
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose} color="secondary">Close</Button>
            <Button href={job.url} target="_blank" rel="noopener noreferrer" variant="contained" color="primary">
              View Original Posting
            </Button>
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